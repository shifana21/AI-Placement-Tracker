from django.core.management.base import BaseCommand
from apps.aptitude.models import AptitudeQuestion

QUESTIONS_DATA = [
    # QUANTITATIVE - EASY
    {
        "category": AptitudeQuestion.Category.QUANTITATIVE,
        "topic": "Percentages",
        "difficulty": AptitudeQuestion.Difficulty.EASY,
        "question_text": "What is 20% of 250?",
        "option_a": "40",
        "option_b": "50",
        "option_c": "60",
        "option_d": "45",
        "correct_option": "B",
        "explanation": "20% of 250 = (20 / 100) * 250 = 50.",
        "marks": 1,
    },
    {
        "category": AptitudeQuestion.Category.QUANTITATIVE,
        "topic": "Profit and Loss",
        "difficulty": AptitudeQuestion.Difficulty.EASY,
        "question_text": "An item bought for $100 is sold for $120. What is the profit percentage?",
        "option_a": "15%",
        "option_b": "20%",
        "option_c": "25%",
        "option_d": "30%",
        "correct_option": "B",
        "explanation": "Profit = 120 - 100 = 20. Profit % = (20 / 100) * 100 = 20%.",
        "marks": 1,
    },
    # QUANTITATIVE - MEDIUM
    {
        "category": AptitudeQuestion.Category.QUANTITATIVE,
        "topic": "Percentages",
        "difficulty": AptitudeQuestion.Difficulty.MEDIUM,
        "question_text": "If the price of sugar increases by 25%, by what percent must a household decrease consumption so that expenditure remains unchanged?",
        "option_a": "20%",
        "option_b": "25%",
        "option_c": "15%",
        "option_d": "33.33%",
        "correct_option": "A",
        "explanation": "Reduction % = [r / (100 + r)] * 100 = [25 / 125] * 100 = 20%.",
        "marks": 1,
    },
    {
        "category": AptitudeQuestion.Category.QUANTITATIVE,
        "topic": "Time and Work",
        "difficulty": AptitudeQuestion.Difficulty.MEDIUM,
        "question_text": "A can complete a task in 12 days and B in 24 days. Working together, how many days will they take?",
        "option_a": "6 days",
        "option_b": "8 days",
        "option_c": "9 days",
        "option_d": "10 days",
        "correct_option": "B",
        "explanation": "Combined rate = 1/12 + 1/24 = 3/24 = 1/8. Total time = 8 days.",
        "marks": 1,
    },
    # QUANTITATIVE - HARD
    {
        "category": AptitudeQuestion.Category.QUANTITATIVE,
        "topic": "Time and Work",
        "difficulty": AptitudeQuestion.Difficulty.HARD,
        "question_text": "Pipe A fills a tank in 4 hours, Pipe B in 6 hours, and Pipe C empties it in 12 hours. If all three pipes are opened simultaneously, how long does it take to fill the tank?",
        "option_a": "2.5 hours",
        "option_b": "3 hours",
        "option_c": "3.5 hours",
        "option_d": "4 hours",
        "correct_option": "B",
        "explanation": "Net rate = 1/4 + 1/6 - 1/12 = (3 + 2 - 1)/12 = 4/12 = 1/3. Hence, 3 hours.",
        "marks": 2,
    },
    {
        "category": AptitudeQuestion.Category.QUANTITATIVE,
        "topic": "Speed Distance Time",
        "difficulty": AptitudeQuestion.Difficulty.HARD,
        "question_text": "A train running at 54 km/h takes 20 seconds to pass a pole. What is the length of the train?",
        "option_a": "250 meters",
        "option_b": "300 meters",
        "option_c": "320 meters",
        "option_d": "270 meters",
        "correct_option": "B",
        "explanation": "Speed = 54 * (5/18) = 15 m/s. Length = Speed * Time = 15 * 20 = 300 meters.",
        "marks": 2,
    },

    # LOGICAL - EASY
    {
        "category": AptitudeQuestion.Category.LOGICAL,
        "topic": "Number Series",
        "difficulty": AptitudeQuestion.Difficulty.EASY,
        "question_text": "Find the next number in the series: 3, 6, 12, 24, 48, ?",
        "option_a": "72",
        "option_b": "84",
        "option_c": "96",
        "option_d": "108",
        "correct_option": "C",
        "explanation": "Each term is multiplied by 2: 48 * 2 = 96.",
        "marks": 1,
    },
    {
        "category": AptitudeQuestion.Category.LOGICAL,
        "topic": "Blood Relations",
        "difficulty": AptitudeQuestion.Difficulty.EASY,
        "question_text": "Pointing to a photograph, Ravi said, 'She is the only daughter of my father's only son.' How is the girl related to Ravi?",
        "option_a": "Niece",
        "option_b": "Sister",
        "option_c": "Daughter",
        "option_d": "Cousin",
        "correct_option": "C",
        "explanation": "Ravi's father's only son is Ravi himself. Her daughter is Ravi's daughter.",
        "marks": 1,
    },
    # LOGICAL - MEDIUM
    {
        "category": AptitudeQuestion.Category.LOGICAL,
        "topic": "Syllogisms",
        "difficulty": AptitudeQuestion.Difficulty.MEDIUM,
        "question_text": "Statements: All cats are dogs. All dogs are birds. Conclusions: I. All cats are birds. II. All birds are cats.",
        "option_a": "Only conclusion I follows",
        "option_b": "Only conclusion II follows",
        "option_c": "Both conclusions follow",
        "option_d": "Neither conclusion follows",
        "correct_option": "A",
        "explanation": "Since all cats are dogs and all dogs are birds, by transitive property all cats are birds. Conclusion I follows.",
        "marks": 1,
    },
    {
        "category": AptitudeQuestion.Category.LOGICAL,
        "topic": "Coding-Decoding",
        "difficulty": AptitudeQuestion.Difficulty.MEDIUM,
        "question_text": "If 'LIGHT' is coded as 'MJHIU', how is 'FLAME' coded in the same pattern?",
        "option_a": "GMBNF",
        "option_b": "GMBNF",
        "option_c": "GNBOD",
        "option_d": "GNBNF",
        "correct_option": "A",
        "explanation": "Each letter is shifted by +1: F->G, L->M, A->B, M->N, E->F => GMBNF.",
        "marks": 1,
    },
    # LOGICAL - HARD
    {
        "category": AptitudeQuestion.Category.LOGICAL,
        "topic": "Seating Arrangement",
        "difficulty": AptitudeQuestion.Difficulty.HARD,
        "question_text": "Five people P, Q, R, S, T are sitting in a circle facing the center. P is between Q and R. S is to the immediate right of T. Q is to the immediate left of P. Who is sitting to the immediate left of R?",
        "option_a": "P",
        "option_b": "Q",
        "option_c": "S",
        "option_d": "T",
        "correct_option": "A",
        "explanation": "Looking at the circle, Q is left of P, P is between Q and R, meaning order clockwise is Q, P, R, T, S. Thus immediate left of R facing center is P.",
        "marks": 2,
    },

    # VERBAL - EASY
    {
        "category": AptitudeQuestion.Category.VERBAL,
        "topic": "Vocabulary",
        "difficulty": AptitudeQuestion.Difficulty.EASY,
        "question_text": "Choose the word most nearly opposite in meaning to 'ABUNDANT':",
        "option_a": "Plentiful",
        "option_b": "Scarce",
        "option_c": "Generous",
        "option_d": "Ample",
        "correct_option": "B",
        "explanation": "'Abundant' means existing in large quantities; the antonym is 'Scarce'.",
        "marks": 1,
    },
    {
        "category": AptitudeQuestion.Category.VERBAL,
        "topic": "Sentence Correction",
        "difficulty": AptitudeQuestion.Difficulty.EASY,
        "question_text": "Choose the grammatically correct sentence:",
        "option_a": "Neither of the boys were present.",
        "option_b": "Neither of the boys was present.",
        "option_c": "Neither of the boy was present.",
        "option_d": "Neither of the boy were present.",
        "correct_option": "B",
        "explanation": "'Neither of' takes a singular verb: 'Neither of the boys was present'.",
        "marks": 1,
    },
    # VERBAL - MEDIUM
    {
        "category": AptitudeQuestion.Category.VERBAL,
        "topic": "Sentence Correction",
        "difficulty": AptitudeQuestion.Difficulty.MEDIUM,
        "question_text": "Identify the error in the sentence: 'She had hardly stepped out when the rain has started.'",
        "option_a": "had hardly",
        "option_b": "stepped out",
        "option_c": "when",
        "option_d": "has started",
        "correct_option": "D",
        "explanation": "'has started' should be 'started' (past tense) to match 'had hardly stepped'.",
        "marks": 1,
    },
    {
        "category": AptitudeQuestion.Category.VERBAL,
        "topic": "Synonyms & Antonyms",
        "difficulty": AptitudeQuestion.Difficulty.MEDIUM,
        "question_text": "Choose the synonym of 'CANDID':",
        "option_a": "Secretive",
        "option_b": "Frank",
        "option_c": "Deceptive",
        "option_d": "Hesitant",
        "correct_option": "B",
        "explanation": "'Candid' means truthful and straightforward; frank.",
        "marks": 1,
    },
    # VERBAL - HARD
    {
        "category": AptitudeQuestion.Category.VERBAL,
        "topic": "Reading Comprehension",
        "difficulty": AptitudeQuestion.Difficulty.HARD,
        "question_text": "Which tone best describes a text that carefully considers counterarguments with dispassionate logic?",
        "option_a": "Polemical",
        "option_b": "Sarcastic",
        "option_c": "Analytical",
        "option_d": "Dogmatic",
        "correct_option": "C",
        "explanation": "An analytical tone employs objective evaluation, balance, and logical dissection.",
        "marks": 2,
    },
]


class Command(BaseCommand):
    help = "Seed idempotent development aptitude questions across categories, topics, and difficulties."

    def handle(self, *args, **options):
        created_count = 0
        updated_count = 0

        for item in QUESTIONS_DATA:
            obj, created = AptitudeQuestion.objects.update_or_create(
                category=item["category"],
                topic=item["topic"],
                question_text=item["question_text"],
                defaults={
                    "difficulty": item["difficulty"],
                    "option_a": item["option_a"],
                    "option_b": item["option_b"],
                    "option_c": item["option_c"],
                    "option_d": item["option_d"],
                    "correct_option": item["correct_option"],
                    "explanation": item["explanation"],
                    "marks": item["marks"],
                    "is_active": True,
                },
            )
            if created:
                created_count += 1
            else:
                updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully seeded aptitude questions: {created_count} created, {updated_count} updated."
            )
        )
