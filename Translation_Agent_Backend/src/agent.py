import os
import re
import json
import time
import openai
from src.tools import write_translation
from src.tm import TranslationMemory, remove_whitespace_between_chinese
from dotenv import load_dotenv

load_dotenv()

class BaseAgent:
    def __init__(self, model="gpt-4o", api_key=None, base_url=None, source_lang="en", target_lang="zh", debug=False, retrieval_method="semantic", full_doc_mode=False, n_results=3, k_glossary=10, sliding_window_size=3):
        self.debug = debug
        self.retrieval_method = retrieval_method
        self.full_doc_mode = full_doc_mode
        self.n_results = n_results
        self.k_glossary = k_glossary
        self.sliding_window_size = sliding_window_size
        self.client = openai.OpenAI(
            api_key=api_key or os.getenv("OPENAI_API_KEY"),
            base_url=base_url
        )
        self.model = model
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.tm = TranslationMemory(source_lang=source_lang, target_lang=target_lang)

    def _clean_response(self, text):
        """Removes <think>...</think> blocks from the response text."""
        if not text:
            return ""
        # Use re.DOTALL to match across newlines
        cleaned = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()
        
        # Remove markdown code blocks if any (model might output ```plaintext ... ```)
        cleaned = cleaned.replace("```plaintext", "").replace("```", "").strip()
        return cleaned 

    def translate_segment(self, segment):
        raise NotImplementedError

    def generate_glossary(self, full_text):
        source_lang_name = "English" if self.source_lang == "en" else "Chinese"
        target_lang_name = "Chinese" if self.target_lang == "zh" else "English"
        
        prompt = f"""Generate a glossary of key terms for the following text. 
Format as: Term ({source_lang_name}) : Term ({target_lang_name})

Text:
{full_text}

Glossary:"""
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}]
        )
        return self._clean_response(response.choices[0].message.content)

    def _process_segments_generator(self, text):
        """Generates translated segments from input text."""
        if self.full_doc_mode:
            if self.debug: print("DEBUG: Running in Full Document Mode")
            segments = [text.strip()]
        else:
            segments = [s.strip() for s in text.split('\n') if s.strip()]

        history = [] # List of {'source': ..., 'target': ...}
        
        for segment in segments:
            # Pass history to translate function
            translation = self.translate_segment(segment, previous_context=history)
            
            yield segment, translation
            
            # Update history
            history.append({'source': segment, 'target': translation})
            if len(history) > self.sliding_window_size:
                history.pop(0) # Keep sliding window

    def process_text(self, text):
        """translates the input string and returns the translated string."""
        translated_parts = []
        for _, translation in self._process_segments_generator(text):
            translated_parts.append(translation)
        return "\n".join(translated_parts)

    def run(self, input_file, output_file):
        with open(input_file, 'r', encoding='utf-8') as f:
            text = f.read()
            
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("")

        translated_segments = []
        
        for segment, translation in self._process_segments_generator(text):
            write_translation(output_file, translation)
            translated_segments.append(translation)
            print(f"Translated: {segment[:20]}... -> {translation[:20]}...")

        #glossary = self.generate_glossary(text)
        #glossary_file = output_file.replace(".txt", "_glossary.txt")
        #with open(glossary_file, 'w', encoding='utf-8') as f:
        #    f.write(glossary)
        #print(f"Glossary generated at {glossary_file}")


class SimpleAgent(BaseAgent):
    def translate_segment(self, segment, previous_context=None):
        source_lang_name = "English" if self.source_lang == "en" else "Chinese"
        target_lang_name = "Chinese" if self.target_lang == "zh" else "English"

        # Note: SimpleAgent does not use previous_context per definition (simple), but needs signature match.
        # Or we could enhance it too. Let's keep it simple for now but matching signature.

        system_msg = f"You are a professional translator from {source_lang_name} to {target_lang_name}. Refrain from using Simplified Chinese and only use traditional Chinese.\nConstraint: Output ONLY the translated text. Do not output anything else."
        
        user_content = f"Source Text:\n{segment}\n\nTranslation:"

        messages = [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": "Source Text:\nHello world\n\nTranslation:"},
            {"role": "assistant", "content": "你好，世界"},
            {"role": "user", "content": user_content}
        ]

        if self.debug: print("DEBUG: Calling LLM (Simple)...")
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages
        )
        if self.debug: print("DEBUG: LLM returned")
        content = response.choices[0].message.content
        return self._clean_response(content)


class ContextAgent(BaseAgent):
    def translate_segment(self, segment, previous_context=None):
        if self.debug: print("DEBUG: ContextAgent start")
        
        matches = []
        if self.retrieval_method == "bm25":
            matches = self.tm.search_bm25(segment)
            if self.debug: print("DEBUG: BM25 search done")
        else:
            matches = self.tm.search_semantic(segment)
            if self.debug: print("DEBUG: Semantic search done")
        
        if self.debug:
            print(f"\n[DEBUG] Segment: {segment}")
            print(f"[DEBUG] Matches ({self.retrieval_method}): {json.dumps(matches, ensure_ascii=False, indent=2)}")
        
        tm_context = ""
        
        # Add Previous Paragraph Context
        if previous_context:
            tm_context += "Previous Context (Use for style and continuity):\n"
            for item in previous_context:
                tm_context += f"- Source: {item['source']}\n  Translation: {item['target']}\n"
            tm_context += "\n"
        
        # Search Contextual Glossary
        if self.debug: print("DEBUG: Glossary search start")
        # Search Contextual Glossary
        if self.debug: print("DEBUG: Glossary search start")
        glossary_terms = self.tm.glossary.search(segment, k_terms=self.k_glossary)
        if self.debug: print("DEBUG: Glossary search done")
        if self.debug:
            print(f"[DEBUG] Glossary Terms: {json.dumps(glossary_terms, ensure_ascii=False, indent=2)}")
        if glossary_terms:
             # ...
            tm_context += "Glossary Terms (Contextual):\n"
            for term, trans in glossary_terms.items():
                tm_context += f"- {term}: {trans}\n"
            tm_context += "\n"

        if self.retrieval_method == "bm25":
            matches = self.tm.search_bm25(segment, n_results=self.n_results)
            if self.debug: print("DEBUG: BM25 search done")
        else:
            matches = self.tm.search_semantic(segment, n_results=self.n_results)
            if self.debug: print("DEBUG: Semantic search done")

        
        source_lang_name = "English" if self.source_lang == "en" else "Chinese"
        target_lang_name = "Chinese" if self.target_lang == "zh" else "English"

        system_msg = f"You are a professional translator from {source_lang_name} to {target_lang_name}. Refrain from using Simplified Chinese and only use traditional Chinese.\nConstraint: Output ONLY the translated text. Do not output anything else."
        
        user_content = f"""Use the provided Translation Memory (TM) and Previous Context to ensure consistency and continuity.

Context & Memory:
{tm_context}

Source Text:
{segment}

Translation:"""

        messages = [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_content}
        ]

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages
        )
        content = response.choices[0].message.content
        return self._clean_response(content)


class ToolAgent(BaseAgent):
    def _research_phase(self, segment):
        """Phase 1: Research the segment using tools."""
        if self.debug: print("DEBUG: Starting Research Phase...")
        
        system_msg = """You are a translation researcher. Your job is to ANALYZE the source text and use tools to gather information to help with translation.
DO NOT TRANSLATE the text yourself.
1. Identify difficult terms, acronyms, or specific nouns and use 'glossary_search' to find their definitions.
2. Use 'search_semantic' to find similar sentences in the Translation Memory for reference.
Output a summary of the research based on what you have found.
Constraint: Output ONLY the summary. Do not output anything else."""
        messages = [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": f"Source text:\n{segment}"}
        ]

        search_tool_desc = "Search for semantically similar segments in the Translation Memory."
        if self.retrieval_method == "bm25":
            search_tool_desc = "Search for keywords in the Translation Memory (BM25)."

        tools = [
            {
                "type": "function",
                "function": {
                    "name": "glossary_search",
                    "description": "Search for definitions of specific terms in the glossary.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "terms": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of terms to look up."
                            }
                        },
                        "required": ["terms"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "search_tm",
                    "description": search_tool_desc,
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "The source text or keywords to search for."},
                            "n_results": {"type": "integer", "description": f"Number of results to return (default {self.n_results})."}
                        },
                        "required": ["query"]
                    }
                }
            }
        ]
        
        # We might need multiple turns if the model wants to call multiple tools sequentially
        MAX_TURNS = 2
        research_summary = ""
        seen_terms = set()
        seen_tm_sources = set()

        for turn in range(MAX_TURNS):
            if self.debug: print(f"DEBUG: Research Turn {turn + 1}")
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=tools,
                tool_choice="auto" 
            )
            
            response_message = response.choices[0].message
            
            if not response_message.tool_calls:
                if self.debug: print("DEBUG: No tool calls, research phase complete.")
                break
                
            # Add assistant message with tool calls to history
            messages.append(response_message)
            
            for tool_call in response_message.tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                
                if self.debug:
                    print(f"[DEBUG] Research Tool Call: {function_name}")
                    print(f"[DEBUG] Arguments: {json.dumps(function_args, ensure_ascii=False)}")

                # Format output as natural language string
                tool_output_str = ""
                
                if function_name == "glossary_search":
                    tool_output = self.tm.glossary.lookup_terms(function_args.get("terms"), context=segment)
                    if tool_output:
                        new_findings = False
                        temp_str = f"Found the following definitions in the glossary:\n"
                        for term, definition in tool_output.items():
                            if term not in seen_terms:
                                temp_str += f"- {term}: {definition}\n"
                                seen_terms.add(term)
                                new_findings = True
                        
                        if new_findings:
                            research_summary += temp_str + "\n"
                            tool_output_str = temp_str # For tool conversation history
                        else:
                            tool_output_str = "No NEW glossary terms found."
                    else:
                        tool_output_str = "No glossary terms found for the requested items."

                elif function_name == "search_tm" or function_name == "search_semantic": 
                    # Support both names for backward compatibility if model hallucinates or old logic
                    n = function_args.get("n_results", self.n_results)
                    
                    start_results = []
                    if self.retrieval_method == "bm25":
                         start_results = self.tm.search_bm25(function_args.get("query"), n_results=n)
                    else:
                         start_results = self.tm.search_semantic(function_args.get("query"), n_results=n)
                    
                    cleaned_results = []
                    for item in start_results:
                        item['target'] = remove_whitespace_between_chinese(item['target'])
                        cleaned_results.append(item)
                    
                    if cleaned_results:
                        new_findings = False
                        temp_str = f"Found the following similar segments in the Translation Memory:\n"
                        for item in cleaned_results:
                            if item['source'] not in seen_tm_sources:
                                temp_str += f"- Source: {item['source']}\n  Target: {item['target']}\n"
                                seen_tm_sources.add(item['source'])
                                new_findings = True
                        
                        if new_findings:
                            research_summary += temp_str + "\n"
                            tool_output_str = temp_str
                        else:
                            tool_output_str = "No NEW similar segments found."
                    else:
                        tool_output_str = "No similar segments found in the Translation Memory."
                
                # Append tool output to conversation history so model sees it
                messages.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": function_name,
                    "content": tool_output_str
                })

        if self.debug: print("DEBUG: Research Summary:\n", research_summary)
        return research_summary

    def _translation_phase(self, segment, research_summary, previous_context=None):
        """Phase 2: Translate using the gathered research."""
        if self.debug: print("DEBUG: Starting Translation Phase...")
        
        source_lang_name = "English" if self.source_lang == "en" else "Chinese"
        target_lang_name = "Chinese" if self.target_lang == "zh" else "English"

        system_msg = f"""You are a professional translator from {source_lang_name} to {target_lang_name}. Use the provided Research Findings and Previous Context to produce a high-quality translation of the source text. Refrain from using Simplified Chinese and only use traditional Chinese.
Constraint: Output ONLY the translated text. Do not output anything else."""
        user_content = ""
        
        
        if previous_context:
            user_content += "Previous Context (Reference Only - Do NOT Translate):\n"
            for item in previous_context:
                user_content += f"- {item['source']} -> {item['target']}\n"
            user_content += "\n"
            
        if research_summary:
            user_content += f"Research Findings:\n{research_summary}\n"
        user_content = f"Source Text:\n{segment}\n\n"
        user_content += "\nTranslation:"
        
        messages = [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_content}
        ]
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages
        )
        
        content = response.choices[0].message.content
        return self._clean_response(content)

    # _extract_json_translation removed (using BaseAgent's)

    def translate_segment(self, segment, previous_context=None):
        # 1. Research
        research_summary = self._research_phase(segment)
        
        # 2. Translate
        translation = self._translation_phase(segment, research_summary, previous_context)
        
        return translation

