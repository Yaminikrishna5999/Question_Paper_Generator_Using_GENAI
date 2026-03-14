import google.generativeai as genai
from config import Config
import time
import re

def generate_with_retry(client, model_name, contents):
    """Wrapper for handling 429 Resource Exhausted rate limitations on free tier."""
    try:
        model = genai.GenerativeModel(model_name)
        return model.generate_content(contents)
    except Exception as e:
        err_msg = str(e).lower()
        if "resource_exhausted" in err_msg or "429" in err_msg:
            print("[Rate Limit] Quota exceeded. Waiting 60 seconds before retrying...")
            time.sleep(60)
            return model.generate_content(contents)
        else:
            raise e

class QuestionGenerator:
    def __init__(self, api_key=None):
        # Configure FREE Gemini API
        usable_key = api_key or Config.GEMINI_API_KEY
        genai.configure(api_key=usable_key)
        self.generated_questions = []
        self.errors = []  # Track errors for UI display
        self.current_model = Config.AI_MODEL
        self._exhausted_models = set()  # Models whose daily quota is done
    
    @staticmethod
    def validate_key(key):
        """Returns (ok:bool, err_code:str)"""
        if not key:
            return False, "no_key"
        try:
            genai.configure(api_key=key)
            # Using a simple prompt to validate the key
            response = generate_with_retry(None, Config.AI_MODEL, "Reply with 'OK'")
            if response.text:
                return True, ""
            return False, "invalid"
        except Exception as e:
            s = str(e).lower()
            if "invalid" in s or "403" in s: return False, "invalid"
            if "quota" in s: return False, "quota"
            return False, f"other:{str(e)}"
    
    def _get_working_model(self):
        """Return a model that hasn't been quota-exhausted today"""
        if self.current_model not in self._exhausted_models:
            return self.current_model
        
        # Build dynamic fallback list via API (resolves 404s for keys that lack certain models)
        dynamic_fallbacks = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        
        for model in dynamic_fallbacks:
            if model not in self._exhausted_models:
                self.current_model = model
                print(f"[Model Switch] Switching to {model}")
                return model
                
        # All exhausted — reset and try first one (maybe quota refreshed)
        self._exhausted_models.clear()
        if dynamic_fallbacks:
            self.current_model = dynamic_fallbacks[0]
        else:
            self.current_model = Config.AI_MODEL
        return self.current_model
    
    def generate_question(self, topic, difficulty, question_type, marks=None, _retry_count=0, pdf_context=None):
        """Generate a single question using FREE Gemini API with automatic model fallback"""
        
        MAX_RETRIES = 2
        MAX_DUPLICATE_RETRIES = 2
        
        prompt = self._build_prompt(topic, difficulty, question_type, pdf_context=pdf_context)
        model = self._get_working_model()
        
        try:
            # Small delay to stay within free-tier rate limits
            time.sleep(2)
            
            # Generate using FREE Gemini
            response = generate_with_retry(None, model, prompt)
            question_text = response.text
            
            # Parse and structure the question (separate question from answer)
            structured_question = self._parse_question(
                question_text, topic, difficulty, question_type, marks
            )
            
            # Check for duplicates (with recursion guard)
            if not self._is_duplicate(structured_question):
                self.generated_questions.append(structured_question)
                return structured_question
            elif _retry_count < MAX_DUPLICATE_RETRIES:
                return self.generate_question(topic, difficulty, question_type, marks, _retry_count + 1, pdf_context)
            else:
                self.generated_questions.append(structured_question)
                return structured_question
                
        except Exception as e:
            error_str = str(e)
            error_msg = f"Error generating {question_type} on '{topic}' ({difficulty}): {e}"
            print(error_msg)
            self.errors.append(error_msg)
            
            is_quota = '429' in error_str or 'RESOURCE_EXHAUSTED' in error_str
            is_daily_quota = is_quota and 'PerDay' in error_str
            
            if is_daily_quota:
                # Daily quota exhausted — mark model and immediately try next
                self._exhausted_models.add(model)
                print(f"[Quota] Daily quota exhausted for {model}, trying fallback...")
                next_model = self._get_working_model()
                if next_model != model:
                    return self.generate_question(topic, difficulty, question_type, marks, 0, pdf_context)
            
            # Retry with backoff for rate limit errors
            if _retry_count < MAX_RETRIES:
                wait_time = 15 if is_quota else 3
                time.sleep(wait_time)
                return self.generate_question(topic, difficulty, question_type, marks, _retry_count + 1, pdf_context)
            return None
    
    def build_academic_prompt(self, cfg, set_label, prev_qs=None):
        """Standardized university exam paper prompt with high-quality generation focus."""
        qtypes   = cfg.get("question_types",["MCQ","Short Answer"])
        q_cnt    = cfg.get("total_questions",10)
        
        # Build specific type requirements string (calculate balanced if missing)
        counts = cfg.get("counts_per_type", {})
        if not counts and qtypes:
            per_type = q_cnt // len(qtypes)
            rem = q_cnt % len(qtypes)
            counts = {qt: per_type + (1 if i < rem else 0) for i, qt in enumerate(qtypes)}
            
        # Ensure q_cnt matches the sum of individual counts for prompt consistency
        q_cnt = sum(counts.values())
        type_reqs = ", ".join([f"{counts.get(qt, 1)} {qt}" for qt in qtypes])
        
        bloom    = ", ".join(cfg.get("bloom",["Remember","Understand"]))
        sections = ", ".join([f"Section {chr(65+i)}" for i in range(cfg.get("num_sections",3))])
        
        marks_ln = "\n".join([f"  - {qt}: {cfg.get('marks_per_type', {}).get(qt, 5)} marks" for qt in qtypes])
        prev_note = f"\n\nAVOID THESE EXISTING QUESTIONS:\n{prev_qs}" if prev_qs else ""
        
        is_file_mode = cfg.get("source_mode") == "File Upload" and bool(cfg.get("file_content"))
        exam_name = cfg.get('exam_name','Standard Examination')
        semester  = cfg.get('semester','')
        instructions = cfg.get('instructions', '')
        instr_note = f"\nFOLLOW THESE INSTRUCTIONS FOR DISTRIBUTION & FORMATTING:\n{instructions}" if instructions else ""
        
        if is_file_mode:
            # Construct prompt for File Mode
            return f"""You are a professional university professor.
Generate EXACTLY {q_cnt} unique questions based EXCLUSIVELY on the provided source text.
The distribution must be precisely: {type_reqs}.

<SOURCE_TEXT>
{cfg['file_content'][:50000]}
</SOURCE_TEXT>

STRICT REQUIREMENTS:
1. NO INTRODUCTORY TEXT: Start directly with "1. [Difficulty][Type] Question".
2. ZERO OUTSIDE KNOWLEDGE: All questions and answers MUST be derived EXCLUSIVELY from the provided <SOURCE_TEXT>.
3. CONCISE QUESTIONS: Question length MUST be independent of marks. For 10-mark questions, the text MUST be concise (max 2-3 sentences or 3-4 lines). Do NOT generate 10 lines of text just because it is worth 10 marks.
4. STUDENT CLARITY: Use simple, direct language. The goal of the question must be immediately obvious.
5. ACCURACY: All questions and answers MUST be factually correct based ON THE SOURCE TEXT ONLY.
6. UNDERSTANDABILITY: Use clear, academic language. Ensure follow-up steps in traces are logically consistent.
7. ABSOLUTE ANSWER ACCURACY: You MUST provide the CORRECT and ABSOLUTE answer for every question based EXCLUSIVELY on the <SOURCE_TEXT>. Do not be vague.
8. NO NUMBERED LISTS IN ANSWERS: Use bullet points (-) or letters (i, ii...) for lists within an answer. NEVER use "1.", "2." etc. inside an answer.
9. MCQ FORMAT: Exactly 4 options (a, b, c, d) VERTICALLY.
10. NO REDUNDANT TAGS: Keep the question body clean. Do not include marks or metadata in the question text.
11. COMPLETE DISTRIBUTION: You MUST generate questions for EVERY type listed in the distribution. Do not skip any type (e.g., if Short Answer is requested, it MUST be generated).

PAPER STRUCTURE:
- EXAM: {exam_name} | Set {set_label} | {semester}
- SECTIONS: {sections}
- DISTRIBUTION: {type_reqs} (Total: {q_cnt} questions){instr_note}
- BLOOM LEVELS: {bloom}
- MARKS: {marks_ln}

FORMAT:
1. [DIFFICULTY][TYPE] Question text?
a) Option 1
b) Option 2
c) Option 3
d) Option 4
CORRECT_ANSWER: [Absolute Correct Answer/Explanation]
Marks: [Value]

Start generating now starting from 1:"""
        else:
            # Manual Mode
            course = f"Course: {cfg.get('course_name','')} ({cfg.get('course_code','')}) | Dept: {cfg.get('department','')}"
            units = f"Units: {', '.join(cfg.get('units',[])) or 'all units'}"
            raw_topics = cfg.get('topics', 'General')
            topics = f"Topics: {', '.join(raw_topics) if isinstance(raw_topics, list) else raw_topics}"
            
            return f"""You are a professional academic expert. 
Generate EXACTLY {q_cnt} unique university-level questions based on the following metadata.
The distribution must be precisely: {type_reqs}.

EXAM: {exam_name} | {course} | {semester} | Set {set_label}
{units} | {topics} | Sections: {sections}{instr_note}

{prev_note}

STRICT REQUIREMENTS:
1. NO INTRODUCTORY TEXT: Start directly with "1. [Difficulty][Type] Question".
2. ZERO OUTSIDE KNOWLEDGE: Base questions ONLY on the provided Topics/Context. Do not use general knowledge outside these subjects.
3. CONCISE QUESTIONS: Regardless of marks, keep the question text brief and focused. Even for 10-mark questions, the text MUST be concise (max 2-3 sentences or 3-4 lines). Do NOT generate 10 lines of text just because it is worth 10 marks.
4. STUDENT CLARITY: Phrase questions simply and directly so they are easy for students to understand.
5. ACCURACY: Ensure the answer is exactly correct for the question. Logic must be flawless.
6. UNDERSTANDABILITY: Questions must be grammatically perfect and easy for students to follow.
7. ABSOLUTE ANSWER ACCURACY: You MUST generate the CORRECT and ABSOLUTE answer for every question. Logic must be flawless.
8. NO NUMBERED LISTS IN ANSWERS: Use bullet points (-) or letters (i, ii...) for lists within an answer. NEVER use "1.", "2." etc. inside an answer.
9. MCQ FORMAT: List options a, b, c, d VERTICALLY. Use the number format "1. " for questions.
10. NO REDUNDANT TAGS: Do not include metadata like "[2 Marks]" inside the question body.
11. COMPLETE DISTRIBUTION: You MUST generate questions for EVERY type listed in the distribution. Do not skip any type (e.g., if Short Answer is requested, it MUST be generated).

FORMAT:
1. [DIFFICULTY][TYPE] Question text?
a) Option 1
b) Option 2
c) Option 3
d) Option 4
CORRECT_ANSWER: [Absolute Correct Answer/Explanation]
Marks: [Value]

Start generating now starting from 1:"""

    def generate_batch(self, prompt, _retry_count=0):
        """Standardized batch generation with automatic model fallback."""
        model = self._get_working_model()
        try:
            time.sleep(1)
            response = generate_with_retry(None, model, prompt)
            if not response or not response.text:
                return None
            return response.text
        except Exception as e:
            err_msg = str(e).lower()
            if "429" in err_msg or "quota" in err_msg or "404" in err_msg:
                if _retry_count < 5:
                    self._exhausted_models.add(model)
                    return self.generate_batch(prompt, _retry_count + 1)
            self.errors.append(f"Generation error ({model}): {str(e)}")
            return None
    @staticmethod
    def clean_metadata(line_text):
        """Removes leading Q#. and all bracketed [METADATA] patterns from the beginning of a line."""
        # 1. Remove leading numbering (e.g., "1. ", "Q1. ", "1) ")
        cleaned = re.sub(r'^(Q?\d+[\.\:\)]\s*)', '', line_text, flags=re.I).strip()
        
        # 2. Generic Bracket Removal: Remove any [...] at the start of the text
        # This handles [EASY], [MCQ], [Very Short Answer] etc. without needing a keyword list.
        while cleaned.startswith('['):
            # Find the closing bracket that matches the first opening bracket
            match = re.search(r'^\[.*?\]', cleaned)
            if match:
                cleaned = cleaned[match.end():].strip()
            else:
                break
        
        return cleaned

    def parse_academic_batch(self, raw, cfg):
        """Robust parser for [DIFFICULTY][TYPE][BLOOM] format with complete index safety."""
        if not raw: return []
        
        # ── DISCARD CHATTER ──
        # Find the first occurrence of "1." or "Q1." to start parsing.
        start_match = re.search(r'(^|\n)(Q?\d+[\.\:\)])', raw)
        if start_match:
            raw = raw[start_match.start():].strip()
        else:
            return [] # No formatted questions found
            
        # ── ROBUST BLOCK SPLITTING ──
        # Split on numbered starts: "1. ", "Q1. ", "1) " at the start of a line.
        # We ALSO split on explicit Section headers like "Section B:" to avoid merging them.
        raw_blocks = re.split(r'\n(?=Q?\d+[\.\:\)]\s*|Section\s+[A-Z][\.\:]\s*)', raw)
        qs = []
        qtypes = cfg.get("question_types", ["MCQ", "Short Answer"])
        # Map each type to a specific section sequentially
        type_to_sec = {qt: f"Section {chr(65+i)}" for i, qt in enumerate(qtypes)}
        
        topics = cfg.get("topics") or ["General"]
        for i, blk in enumerate(raw_blocks):
            if not blk.strip(): continue
            lines = blk.strip().split('\n')
            
            # 1. Metadata extraction (Precise search for configured types)
            dm = re.search(r'\[(EASY|MEDIUM|HARD)\]', blk, re.I)
            bm = re.search(r'\[(Remember|Understand|Apply|Analyze|Evaluate|Create)\]', blk, re.I)
            
            # Precise Question Type Matching:
            # We check the block for ANY of the user-selected types explicitly.
            qtype = None
            for qt in qtypes:
                if re.search(rf'\[{re.escape(qt)}\]', blk, re.I):
                    qtype = qt
                    break
            
            if not qtype:
                # Secondary check: if [Type] is missing, check content
                lblk = blk.lower()
                if "mcq" in lblk or "multiple choice" in lblk: qtype = "MCQ"
                elif "short" in lblk: qtype = "Short Answer"
                elif "long" in lblk: qtype = "Long Answer"
                else:
                    # If it's a small fragment and we're not at the first block, 
                    # it's likely a continuation of the PREVIOUS answer (e.g. from internal list parsing error)
                    if i > 0 and len(qs) > 0:
                        # Append to previous answer if no tags and it looks like a continuation
                        if not dm and not bm:
                            qs[-1]["a"] += "\n" + blk.strip()
                            continue
                    qtype = qtypes[i % len(qtypes)] if qtypes else "Short Answer"
            
            # Normalize qtype specifically for section mapping (matching UI strings exactly)
            qtype_orig = qtype
            qtype_norm = qtype.lower()
            
            if "very short" in qtype_norm: qtype = "Very Short Answer"
            elif "short" in qtype_norm and "very" not in qtype_norm: qtype = "Short Answer"
            elif "long" in qtype_norm: qtype = "Long Answer"
            elif "fill" in qtype_norm: qtype = "Fill in the Blanks"
            elif "descriptive" in qtype_norm: qtype = "Descriptive Questions"
            elif "mcq" in qtype_norm or "multiple choice" in qtype_norm: qtype = "MCQ"
            
            # Final fallback: if normalized type is not in selected types, try to find a partial match
            if qtype not in qtypes:
                for qt in qtypes:
                    if qt.lower() in qtype_norm:
                        qtype = qt
                        break
            
            diff = {"EASY":"Easy","MEDIUM":"Medium","HARD":"Hard"}.get(dm.group(1).upper() if dm else "MEDIUM", "Medium")
            bloom = bm.group(1).capitalize() if bm else "Remember"
            
            ans, marks_val = "See model answer.", cfg.get('marks_per_type', {}).get(qtype, 5)
            
            parsing_mode = "QUESTION" # Modes: QUESTION, OPTIONS
            qtxt_lines = []
            options_list = []
            
            for ln in lines:
                ls = ln.strip()
                if not ls: continue
                l_lower = ls.lower()
                
                # Check for terminators
                if l_lower.startswith("correct_answer:") or l_lower.startswith("answer:"):
                    parts = ln.split(":", 1)
                    ans = parts[1].strip() if len(parts) > 1 else ""
                    parsing_mode = "ANSWER"
                    continue
                elif l_lower.startswith("marks:"):
                    m_match = re.search(r'\d+', ls)
                    if m_match: marks_val = int(m_match.group())
                    parsing_mode = "DONE"
                    continue
                
                # Check for options start (only in MCQ)
                if parsing_mode == "QUESTION" and re.match(r'^[a-d][\.\)]', ls, re.I):
                     parsing_mode = "OPTIONS"
                
                if parsing_mode == "QUESTION":
                    # Clean tags and leading number from first line of question
                    cleaned = QuestionGenerator.clean_metadata(ls)
                    if cleaned:
                        qtxt_lines.append(cleaned)
                elif parsing_mode == "OPTIONS":
                    # Remove option label prefix for structured storage (ExportHandler adds them back)
                    opt_content = re.sub(r'^[a-d][\.\)]\s*', '', ls, flags=re.I).strip()
                    if opt_content:
                        options_list.append(opt_content)
                elif parsing_mode == "ANSWER":
                    # Capture multi-line answer content
                    if ans:
                        ans += "\n" + ls
                    else:
                        ans = ls

            qtxt = "\n".join(qtxt_lines).strip() # PRESERVE NEWLINES
            ans = ans.replace("*", "").strip() # Strip clumsy AI asterisks
            if not qtxt: continue

            # FINAL SAFE INDEXING
            safe_topic = topics[i % len(topics)] if topics else "General"
            
            qs.append({
                "no": i+1, "number": i+1,
                "q": qtxt, 
                "content": qtxt + (("\nOptions:\n" + "\n".join(options_list)) if options_list else ""), 
                "options": options_list,
                "a": ans,
                "type": qtype, "difficulty": diff, "bloom": bloom, "marks": marks_val,
                "topic": safe_topic,
                "section": type_to_sec.get(qtype, "Section A")
            })
            
        # Final Step: Sort questions by section to ensure perfect grouping (e.g., Section A, then B...)
        qs.sort(key=lambda x: x.get("section", "Section A"))
        
        # Re-index numbers after sorting for clean sequential listing
        for idx, q in enumerate(qs):
            q["no"] = idx + 1
            q["number"] = idx + 1

        return qs

    def _build_prompt(self, topic, difficulty, question_type, pdf_context=None):
        """Build AI prompt based on parameters, optionally using PDF syllabus content"""
        
        # If PDF content is provided, prepend it as rich context
        if pdf_context:
            context_block = f"""You are a professional exam setter. Below is the full syllabus/content extracted from the uploaded course material. 
Use this content as your primary source of knowledge to generate the question:

--- SYLLABUS CONTENT START ---
{pdf_context}
--- SYLLABUS CONTENT END ---

Now, based strictly on the above content, """
        else:
            context_block = ""
        prompts = {
            'MCQ': f"""{context_block}generate a {difficulty} level multiple-choice question about: {topic}

Requirements:
- Clear, unambiguous question
- 4 options (A, B, C, D)
- Only ONE correct answer
- Distractors should be plausible but incorrect
- Academic and professional language

Format your response EXACTLY as (each option on its own line):
QUESTION: [question text]
A) [option]
B) [option]
C) [option]
D) [option]
ANSWER: [letter]""",

            'Short Answer': f"""{context_block}generate a {difficulty} level short answer question about: {topic}

Requirements:
- Requires 2-4 sentence answer
- Tests conceptual understanding
- Clear and specific
- Academic language

Format your response EXACTLY as:
QUESTION: [question text]
ANSWER: [brief model answer in 2-4 sentences]""",

            'Long Answer': f"""{context_block}generate a {difficulty} level long answer/essay question about: {topic}

Requirements:
- Requires detailed explanation (1-2 paragraphs)
- Tests deep understanding and analysis
- Open-ended but focused
- Academic language

Format your response EXACTLY as:
QUESTION: [question text]
ANSWER: [key points to cover as bullet points]""",

            'True/False': f"""{context_block}generate a {difficulty} level True/False question about: {topic}

Requirements:
- Clear, definitive statement
- Unambiguous correct answer
- Academic language

Format your response EXACTLY as:
QUESTION: [statement]
ANSWER: [True/False]
EXPLANATION: [brief justification]""",

            'Fill in the Blanks': f"""{context_block}generate a {difficulty} level fill-in-the-blank question about: {topic}

Requirements:
- Use _____ for blank
- Only one blank per question
- Clear context
- Academic language

Format your response EXACTLY as:
QUESTION: [question with _____ ]
ANSWER: [answer]"""
        }
        
        return prompts.get(question_type, prompts['MCQ'])
    
    def _extract_question_and_answer(self, raw_text, question_type):
        """Separate question content from answer content"""
        
        text = raw_text.strip()
        question_part = ""
        answer_part = ""
        
        if question_type == 'MCQ':
            # Split at ANSWER: or Correct Answer:
            match = re.search(r'(ANSWER\s*:|Correct\s+Answer\s*:)', text, re.IGNORECASE)
            if match:
                question_part = text[:match.start()].strip()
                answer_part = text[match.start():].strip()
            else:
                question_part = text
                answer_part = ""
            
            # Clean up the question part - remove "QUESTION:" prefix
            question_part = re.sub(r'^QUESTION\s*:\s*', '', question_part, flags=re.IGNORECASE).strip()
                
        elif question_type == 'True/False':
            match = re.search(r'(ANSWER\s*:|Correct\s+Answer\s*:)', text, re.IGNORECASE)
            if match:
                question_part = text[:match.start()].strip()
                answer_part = text[match.start():].strip()
            else:
                question_part = text
                answer_part = ""
            question_part = re.sub(r'^(QUESTION|Statement)\s*:\s*', '', question_part, flags=re.IGNORECASE).strip()
                
        else:
            # Short Answer, Long Answer, Fill in the Blanks
            match = re.search(r'(ANSWER\s*:|Expected\s+Answer\s*:|Key\s+Points\s+to\s+Cover\s*:)', text, re.IGNORECASE)
            if match:
                question_part = text[:match.start()].strip()
                answer_part = text[match.start():].strip()
            else:
                question_part = text
                answer_part = ""
            question_part = re.sub(r'^QUESTION\s*:\s*', '', question_part, flags=re.IGNORECASE).strip()
        
        # FINAL SANITIZATION: Remove any remaining [EASY][MCQ] tags or Q#: headers
        question_part = QuestionGenerator.clean_metadata(question_part)
        return question_part, answer_part
    
    def _parse_question(self, raw_text, topic, difficulty, question_type, marks=None):
        """Parse AI response into structured format with separate question and answer"""
        
        if marks is None:
            # Safe marks lookup
            m_cfg = Config.MARKS_CONFIG.get(difficulty, Config.MARKS_CONFIG.get("Medium", {}))
            marks = m_cfg.get(question_type, 2)
        
        question_part, answer_part = self._extract_question_and_answer(raw_text, question_type)
        
        return {
            'topic': topic,
            'difficulty': difficulty,
            'type': question_type,
            'marks': marks,
            'content': question_part,       # Only the question (no answer)
            'answer': answer_part,           # Answer stored separately
            'full_content': raw_text.strip(), # Original full content for reference
            'timestamp': time.time()
        }
    
    def _is_duplicate(self, new_question):
        """Check if question is duplicate"""
        
        new_content = new_question['content'].lower()
        
        for existing in self.generated_questions:
            existing_content = existing['content'].lower()
            if self._calculate_similarity(new_content, existing_content) > 0.8:
                return True
        
        return False
    
    def _calculate_similarity(self, text1, text2):
        """Basic similarity calculation"""
        
        words1 = set(text1.split())
        words2 = set(text2.split())
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0
    
    def clear_cache(self):
        """Clear generated questions cache"""
        self.generated_questions = []
        self.errors = []
