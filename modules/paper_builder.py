from config import Config
from modules.question_generator import QuestionGenerator
import random

class PaperBuilder:
    def __init__(self):
        self.generator = QuestionGenerator()
        self.progress_callback = None  # Optional progress callback
        self.custom_marks = {}  # Custom marks per question type
        self.exam_metadata = {}  # Exam details
    
    def build_paper(self, topics, total_questions, difficulty_dist, question_types, paper_name="Paper 1", pdf_context=None):
        """Build a complete question paper based on rules"""
        
        # Calculate questions per difficulty
        questions_dist = self._calculate_distribution(total_questions, difficulty_dist)
        
        # Allocate questions to topics
        topic_allocation = self._allocate_to_topics(topics, questions_dist)
        
        # Generate questions
        questions = []
        question_num = 1
        
        # Progress callback support
        total_to_generate = sum(
            count for alloc in topic_allocation.values() for count in alloc.values()
        )
        generated_count = 0
        
        for topic, alloc in topic_allocation.items():
            for difficulty, count in alloc.items():
                for _ in range(count):
                    # Select random question type
                    q_type = random.choice(question_types)
                    
                    # Update progress callback if set
                    generated_count += 1
                    if self.progress_callback:
                        self.progress_callback(generated_count, total_to_generate, topic, difficulty, q_type)
                    
                    # Generate question with custom marks if set
                    marks = self.custom_marks.get(q_type, None)
                    question = self.generator.generate_question(topic, difficulty, q_type, marks=marks, pdf_context=pdf_context)
                    
                    if question:
                        question['number'] = question_num
                        questions.append(question)
                        question_num += 1
        
        # Build paper structure
        paper = {
            'name': paper_name,
            'total_questions': len(questions),
            'total_marks': sum(q['marks'] for q in questions),
            'difficulty_distribution': difficulty_dist,
            'topics': topics,
            'questions': questions,
            'errors': list(self.generator.errors)  # Include any errors
        }
        
        return paper
    
    def _calculate_distribution(self, total, percentages):
        """Calculate exact number of questions per difficulty"""
        
        distribution = {}
        remaining = total
        
        for level in ['Easy', 'Medium']:
            count = round(total * percentages[level] / 100)
            distribution[level] = count
            remaining -= count
        
        # Assign remaining to Hard
        distribution['Hard'] = remaining
        
        return distribution
    
    def _allocate_to_topics(self, topics, difficulty_dist):
        """Distribute questions across topics proportionally"""
        topics = topics or ["General"]
        allocation = {topic: {'Easy': 0, 'Medium': 0, 'Hard': 0} for topic in topics}
        
        for difficulty, total_count in difficulty_dist.items():
            questions_per_topic = total_count // len(topics)
            remainder = total_count % len(topics)
            
            for i, topic in enumerate(topics):
                allocation[topic][difficulty] = questions_per_topic
                if i < remainder:
                    allocation[topic][difficulty] += 1
        
        return allocation
    
    def build_multiple_sets(self, topics, total_questions, difficulty_dist, question_types, num_sets=3, pdf_context=None):
        """Generate multiple unique question paper sets"""
        
        papers = []
        
        for i in range(num_sets):
            # Clear cache for uniqueness across sets
            self.generator.clear_cache()
            
            paper_name = f"Set {chr(65 + i)}"  # Set A, Set B, etc.
            paper = self.build_paper(topics, total_questions, difficulty_dist, question_types, paper_name, pdf_context=pdf_context)
            papers.append(paper)
        
        return papers