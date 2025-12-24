import sys, os
import regex as re
from datetime import datetime #, timedelta
from pathlib import Path #, PurePath
from math import ceil
from random import seed as seed
import numpy as np
#import sqlite3
import torch
from sentence_splitter import SentenceSplitter, split_text_into_sentences
import unicodedata
import pysbd
import ujson
import bz2, lzma, gzip

from dp_utils3way import make_alignment_types, make_alignment_types_fixed_source, \
    read_alignments, read_in_embeddings, make_doc_embedding, vecalign, yield_overlaps

#from score import score_multiple, log_final_scores

from sentence_transformers import SentenceTransformer #, models, util

start_time = datetime.now()
if os.name == 'nt':
    d = 0
elif os.name == 'posix':
    if torch.cuda.is_available():
        d = 0
    elif torch.mps.is_available():
        d = 1
m = 0  # Use Alibaba-GTE 8k-token context window; we're embedding entire articles
dev = ['cuda', 'mps', 'cpu'][d]
#Model we want to use for bitext mining. LaBSE achieves state-of-the-art performance
#model_name = ['LaBSE', 'Alibaba-NLP/gte-multilingual-base', 'paraphrase-multilingual-MiniLM-L12-v2'][m]
model_name = ['Alibaba-NLP/gte-multilingual-base', 'ibm-granite/granite-embedding-278m-multilingual', 'LaBSE', 'paraphrase-multilingual-MiniLM-L12-v2'][m]
model_name_short = ['alibaba-gte-multilingual', 'ibm-granite', 'LaBSE', 'paraphrase'][m]

if 'model' not in globals():
    print(f"Now running bitext mining with transformer model [{model_name}] on device [{dev}]...", flush=True)
    model = SentenceTransformer(model_name, device=dev, trust_remote_code=True)
    print(f"Finished loading model: {model_name}.", flush=True)
else:
    print(f"Model [{model_name}] already loaded", flush=True)

end_time = datetime.now() - start_time
print(f"Model-loading time: {end_time.seconds} secs", flush=True)

#%%
# %%


def encodeVectors(ss, model, dev):
    '''
    Input:
        ss: lit of strings
    Output:
        pytorch tensors
    '''
    vecs = model.encode(ss, show_progress_bar=False, convert_to_numpy=False, normalize_embeddings=True, device=dev)
    return vecs

def print_alignments(alignments, scores=None, file=sys.stdout):
    if scores is not None:
        for (x, y), s in zip(alignments, scores):
            print('%s:%s:%.6f' % (x, y, s), file=file)
    else:
        for x, y in alignments:
            print('%s:%s' % (x, y), file=file)


def file_open(filepath):
    #Function to allowing opening files based on file extension
    if filepath.endswith('.gz'):
        return gzip.open(filepath, 'rt', encoding='utf8')
    elif filepath.endswith('.bz2'):
        return bz2.open(filepath, 'rt', encoding='utf8')
    elif filepath.endswith('.xz'):
        return lzma.open(filepath, 'rt', encoding='utf8')
    else:
        return open(filepath, 'r', encoding='utf8')

def getLines(fin):
    '''
    Retrive lines from a file or (later) sqlite3 database
    '''
    lines = file_open(fin).readlines()
    return [s.strip() for s in lines if s.strip() != '']

def getSentIndex(lines):
    """
    dictionary look-up:
        keys = sentence or overlapped sentences
        value = index
    """
    sent2line = dict()
    for ii, line in enumerate(lines):
        if line.strip() in sent2line:
            raise Exception('got multiple embeddings for the same line')
        sent2line[line.strip()] = ii
    return sent2line

def getOverlaps(lines, num_overlaps):
    output = set()
    for out_line in yield_overlaps(lines, num_overlaps):
        output.add(out_line)

    # for reproducibility
    output = list(output)
    output.sort()
    return output

def normalizeText(text):
    text = text.replace("\xad", '')  # remove Unicode soft hyphen
    return unicodedata.normalize("NFKC", text) # remove Unicode , among others

# Sentence tokenizer

# regex to identify Chinese sentence boundaries
#regex_zh_sent_delim = re.compile(r"([。！？；][」』”〕》〗】)）\]]?)")
#regex_zh_sent_delim = re.compile(r"([。？；][」』”〕》〗】)）\]]?)")
#regex_zh_sent_delim = re.compile(r'(?P<quotation_mark>([。？！…]{1,2})[」』〕》〗】\])”’"\'）])')
#regex_zh_sent_delim = re.compile(r"[。！？]")
regex_zh_sent_delim = re.compile(r"([。？！；：…][」』”’\'\"〕》〗】)）\]]{0,3})")

def normalizeTextZh(text):
    text = text.replace("\xad", '')  # remove Unicode
    #text = text.replace("!", "！").replace(";", "；")
    return unicodedata.normalize("NFKD", text) # remove Unicode , among others

def sentencizeZh(s):
    '''
    turn long string s into a list of sentences
    '''
    s = normalizeTextZh(s)
    s = s.replace(',','，').replace(';','；').replace("!", "！").replace(":", "：").replace("?", "？")
    ss = regex_zh_sent_delim.sub(r"\1\n", s).split("\n")
    return [s.strip() for s in ss if s.strip() != '']


def sentencize(s, lang='en'):
    if lang in ['zh', 'ja']:
        return sentencizeZh(s)
    else: # lang in ['en', 'es', 'fr', 'de', 'it', etc. ]
        splitter = SentenceSplitter(language=lang)
        sentseg = pysbd.Segmenter(language=lang, clean=False)
        s = normalizeText(s)
        ss = splitter.split(text=s)
        #ss = sentseg.segment(s)
        return [s.strip() for s in ss if s.strip() != '']

def convertChinesePunctuations(txt):
    '''
    Convert “”‘’ to, respeectively 「」『』
    '''
    punctHans2Hant = {'“”‘’': '「」『』'}
    for k in punctHans2Hant:
        v = punctHans2Hant[k]
        for ps, pt in zip(k, v):
            txt = txt.replace(ps, pt)
    return txt

#%%
def align(sS, sT, alignment_max_size, langS, langT, alignment_type='normal'):

    # make runs consistent
    seed(42)
    np.random.seed(42)

    # source
    overlapsS = getOverlaps(sS, alignment_max_size)  # create "overlapped" sentences
    s2idxS = getSentIndex(overlapsS)                 # create "sentence-to-index" lookup table
    embedS = encodeVectors(overlapsS, model, dev)    # encode a list of sentences
    src_line_embeddings = torch.vstack(embedS).cpu().numpy()   # turns a list of sentences into a tensor object
    # target
    overlapsT = getOverlaps(sT, alignment_max_size)
    s2idxT = getSentIndex(overlapsT)
    embedT = encodeVectors(overlapsT, model, dev)
    overlapsS = getOverlaps(sS, alignment_max_size)
    tgt_line_embeddings = torch.vstack(embedT).cpu().numpy()

    #print(f"src_line_embeddings has shape: [{src_line_embeddings.shape}]")
    #print(f"tgt_line_embeddings has shape: [{tgt_line_embeddings.shape}]")
    #sys.exit(0)

    width_over2 = ceil(alignment_max_size / 2.0) + 5

    test_alignments = []
    stack_list = []

    #src_lines = open(finS, 'rt', encoding="utf-8").readlines()
    vecs0 = make_doc_embedding(s2idxS, src_line_embeddings, sS, alignment_max_size)

    #tgt_lines = open(finT, 'rt', encoding="utf-8").readlines()
    vecs1 = make_doc_embedding(s2idxT, tgt_line_embeddings, sT, alignment_max_size)

    if alignment_type == 'normal':
        final_alignment_types = make_alignment_types(alignment_max_size)
    elif alignment_type == 'fixed_source':
        final_alignment_types = make_alignment_types_fixed_source(alignment_max_size)
    else:
        print("*** Error alignment_type: Terminated ***")
        return 1

    stack = vecalign(vecs0=vecs0,
                     vecs1=vecs1,
                     final_alignment_types=final_alignment_types,
                     del_percentile_frac=0.2,
                     width_over2=width_over2,
                     max_size_full_dp=300,
                     costs_sample_size=20000,
                     num_samps_for_norm=100)

    # write final alignments to fk\ile
    #print_alignments(stack[0]['final_alignments'], stack[0]['alignment_scores'])
    #test_alignments.append(stack[0]['final_alignments'])
    #stack_list.append(stack)

    alignments = stack[0]['final_alignments']
    scores     = stack[0]['alignment_scores']

    aligned_sentences = []
    if scores is not None:
        for (idxS, idxT), score in zip(alignments, scores):
            sbS  = [] # sentence block - source
            for i in idxS:
                sbS.append(sS[i])
            sbT  = [] # sentence block - target
            for i in idxT:
                sbT.append(sT[i])

            sepS = '' if langS in ['zh', 'ja'] else ' '
            sepT = '' if langT in ['zh', 'ja'] else ' '

            #aligned_sentences.append(f"{score:.5f}\t{idxS}\t{' '.join(sbS)}\t{idxT}\t{' '.join(sbT)}")
            #aligned_sentences.append([score, idxS, ' '.join(sbS), idxT, ' '.join(sbT)])
            aligned_sentences.append([score, idxS, sepS.join(sbS), idxT, sepT.join(sbT)])

    return aligned_sentences
#%%

if __name__ == '__main__':

    alignment_max_size = 5
    print(f"alignment_max_size = {alignment_max_size}")

    ###########################################################
    # Choose language triple (translation direction)
    ###########################################################
    langS  = 'en'       # Source text
    langT1 = 'zh_mt'    # Machine Translation output
    langT2 = 'zh_ref'   # Reference Translation

    out_langS, out_langT1, out_langT2 = langS, langT1, langT2

    ###########################################################
    # Specify input files, output file
    ###########################################################

    ## S (source), Target 1 (T1), Target 2 (T2)
    source_folder = '/Users/rubentsui/NLP/ScientificAmerican'
    base  = f'{source_folder}/SAT_test01'
    finS  = f'{base}.{langS}.txt'
    finT1 = f'{base}.{langT1}.txt'
    finT2 = f'{base}.{langT2}.txt'
    fonST1 = f"{base}.vecalign.n{alignment_max_size}.{model_name_short}.{out_langS}-{out_langT1}.txt"
    fon = f"{base}.vecalign.n{alignment_max_size}.{model_name_short}.{out_langS}-{out_langT1}-{out_langT2}.txt"

    DEBUG = False

    linesS = Path(finS).read_text(encoding='utf-8').strip().split('\n')
    pS = [p.strip() for p in linesS if p.strip()]

    linesT1 = Path(finT1).read_text(encoding='utf-8').strip().split('\n')
    pT1 = [p.strip() for p in linesT1 if p.strip()]

    linesT2 = Path(finT2).read_text(encoding='utf-8').strip().split('\n')
    pT2 = [p.strip() for p in linesT2 if p.strip()]

#%%

    ### Align langS and langT1
    with open(fonST1, "w", encoding="utf-8", newline="\n") as fo:
        for score, idxS, ss, idxT, tt in align(pS, pT1, alignment_max_size=alignment_max_size, langS=langS, langT=langT1):
            fo.write(f"{score:.4f}\t{idxS}\t{ss}\t{idxT}\t{tt}\n")

    ###

#%%

    # We need a new pS from the aligned source from above
    pSnew = []
    pSnew_pT1 = {}
    with open(fonST1, "r", encoding="utf-8") as fi:
        for line in fi:
            score, idxS, ss, idxT, tt = line.strip().split('\t')
            pSnew.append(ss)
            pSnew_pT1[ss] = f"{idxT}\t{tt}"


#%%
    ### Align langS and langT2

    with open(fon, "w", encoding="utf-8", newline="\n") as fo:
        for score, idxS, ss, idxT, tt in align(pSnew, pT2, alignment_max_size=alignment_max_size, langS=langS, langT=langT2, alignment_type='fixed_source'):
            fo.write(f"{score:.4f}\t{idxS}\t{ss}\t{pSnew_pT1[ss]}\t{idxT}\t{tt}\n")


#%%

fin = fon
D = []
with open(fin, 'r', encoding='utf-8') as fi:

    for line in fi:
        score, idxS, ss, idxT1, tt1, idxT2, tt2 = line.strip().split('\t')
        segment = {
                'src': ss,
                'tgt': tt1,
                'ref': tt2
            }
        D.append(segment)


#%%


        #print(f"processing segment:", flush=True)

        # Perform paragraph alignment between langS and langT1
        with open(fon, "a", encoding="utf-8", newline="\n") as fo:

            ch_cnt = 0
            for cS, cT in zip(linesS, linesT1):

                ch_cnt += 1
                print(f"[{ch_cnt}]", flush=True)

                # Source
                pS = cS.strip().replace("\r", "").replace("\n", "")
                sS = pS # sentencize(pS, lang=langS)
                sS = [s.strip() for s in sS if s.strip()!='']

                # Target 1
                pT = cT.strip().split("\n")
                pT = [s.strip() for s in pT if s.strip()!='']
                sT = []
                for p in pT:
                    sT.extend(sentencize(p, lang=langT))
                sT = [s.strip() for s in sT if s.strip()!='']

                if sS and sT:
                    for score, idxS, ss, idxT, tt in align(sS, sT, alignment_max_size=alignment_max_size):
                        fo.write(f"{lawid} {score:.4f}\t{idxS}\t{ss}\t{idxT}\t{tt}\n")
            fo.flush()

        print(f" ==> Law [{lawid}] alignment compeleted.")
