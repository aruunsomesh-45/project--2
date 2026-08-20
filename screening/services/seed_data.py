"""
Full content of the Adaptive Screening Question Bank, transcribed from
Adaptive_Screening_Question_Bank.pdf. Loaded by the `seed_screening`
management command.

Two items in the source PDF had extraction/formatting issues, flagged
inline below with NOTE comments — corrected using the rule stated in the
question itself (the letter-shift pattern) or the obvious logical pattern,
rather than left broken or silently guessed without explanation.
"""

TIERS = ['grade_8_10', 'grade_10_12', 'undergraduate', 'postgraduate']

# ============================================================ PART 1 =======

# Each entry: (topic, difficulty, passage, question_text, options[(label,text)], correct_label)
ADAPTIVE_QUESTIONS_BY_TIER = {
    'grade_8_10': [
        ('Reading Comprehension', 'easy',
         "Meera plants a sapling every year on her birthday to see how much it has grown. "
         "This year, for the first time, the tree is taller than her.",
         "What is this passage mainly about?",
         [('A', 'A birthday party'), ('B', "Meera tracking a tree's growth over the years"),
          ('C', 'Meera being afraid of trees'), ('D', 'A gardening competition')], 'B'),
        ('Reading Comprehension', 'medium',
         "The city council debated the new park for months. Some wanted more benches, others "
         "wanted more trees. In the end, they built a park with both — just fewer of each than "
         "originally planned.",
         "What does this best show?",
         [('A', "The council couldn't agree on anything"),
          ('B', 'A compromise was reached between two competing preferences'),
          ('C', 'The park was cancelled'), ('D', 'Trees are more important than benches')], 'B'),
        ('Reading Comprehension', 'hard',
         "Despite the coach's warnings, the team kept playing an aggressive style. They won more "
         "matches, but injuries piled up, and by the season's end, three key players were out.",
         "What's the most reasonable takeaway?",
         [('A', 'Aggressive play should always be avoided'), ('B', 'The coach was wrong to warn them'),
          ('C', "Their success came with a real cost they'll likely feel next season"),
          ('D', 'Injuries have nothing to do with playing style')], 'C'),

        ('General Awareness', 'easy', '', 'Which of these is a renewable source of energy?',
         [('A', 'Coal'), ('B', 'Solar'), ('C', 'Petroleum'), ('D', 'Natural gas')], 'B'),
        ('General Awareness', 'medium', '',
         "If a region's population grows much faster than its food production, what's the likely long-term challenge?",
         [('A', 'Lower food prices'), ('B', 'Food scarcity'), ('C', 'Less need for farming'), ('D', 'Higher food security')], 'B'),
        ('General Awareness', 'hard', '',
         'A city bans single-use plastic bags. Which outcome is least likely to happen as a direct result?',
         [('A', 'Reduced landfill waste'), ('B', 'More people using reusable bags'),
          ('C', 'Complete elimination of all pollution in the city'), ('D', 'Some short-term inconvenience for shoppers')], 'C'),

        ('Pattern & Code Reasoning', 'easy', '', 'What comes next: A, C, E, G, ___?',
         [('A', 'H'), ('B', 'I'), ('C', 'F'), ('D', 'J')], 'B'),
        ('Pattern & Code Reasoning', 'medium', '', "Which one doesn't belong: BDF, CEG, ACE, BCD?",
         [('A', 'BDF'), ('B', 'CEG'), ('C', 'ACE'), ('D', 'BCD')], 'D'),
        ('Pattern & Code Reasoning', 'hard', '',
         'In a code, CAT is written as DBU (each letter shifted forward by one). How is DOG written in the same code?',
         [('A', 'EPG'), ('B', 'EPH'), ('C', 'DPH'), ('D', 'EOH')], 'B'),

        ('Verbal / Logical Reasoning', 'easy', '', 'Book is to Read as Song is to ___?',
         [('A', 'Sing'), ('B', 'Listen'), ('C', 'Write'), ('D', 'Play')], 'B'),
        ('Verbal / Logical Reasoning', 'medium', '',
         'All squares are rectangles. All rectangles have four sides. Therefore:',
         [('A', 'All rectangles are squares'), ('B', 'All squares have four sides'),
          ('C', 'All four-sided shapes are squares'), ('D', 'No conclusion possible')], 'B'),
        ('Verbal / Logical Reasoning', 'hard', '',
         'Some Zips are Zaps. All Zaps are Zoos. Which must be true?',
         [('A', 'All Zips are Zoos'), ('B', 'Some Zips are Zoos'), ('C', 'No Zips are Zoos'), ('D', 'All Zoos are Zips')], 'B'),
    ],

    'grade_10_12': [
        ('Reading Comprehension', 'easy',
         "Rohan started a weekend job to save for a new laptop. At first his grades dipped slightly, "
         "but after he made a strict study schedule, both his savings and his grades improved.",
         "What helped Rohan improve both his grades and savings?",
         [('A', 'Quitting the job'), ('B', 'A strict schedule that balanced both'),
          ('C', 'Studying less'), ('D', 'Ignoring his job')], 'B'),
        ('Reading Comprehension', 'medium',
         "The new grading policy removed all early deadlines, giving students the entire semester to "
         "submit work. Some teachers praised the flexibility; others noticed a spike in last-minute, "
         "lower-quality submissions near finals week.",
         "What is the passage mainly illustrating?",
         [('A', 'The policy was an unqualified success'), ('B', 'The policy was a total failure'),
          ('C', 'A clear tradeoff between flexibility and quality'), ('D', 'Teachers unanimously disliked the new policy')], 'C'),
        ('Reading Comprehension', 'hard',
         "A study found that students who used a popular study app scored higher on tests, so the app "
         "must be responsible for the improvement.",
         'What is the flaw in this reasoning?',
         [('A', "The study didn't use real students"),
          ('B', 'It assumes correlation means causation, ignoring other explanations (like these being more motivated students to begin with)'),
          ('C', 'The app is objectively bad'), ('D', "Test scores don't matter")], 'B'),

        ('General Awareness', 'easy', '', 'Which of these best describes "sustainable development"?',
         [('A', 'Growth that ignores environmental impact'),
          ('B', "Meeting present needs without compromising future generations' ability to meet theirs"),
          ('C', 'Rapid industrialization at any cost'), ('D', 'Development only in urban areas')], 'B'),
        ('General Awareness', 'medium', '',
         "A country's currency loses value rapidly compared to others. Which is a likely direct effect?",
         [('A', 'Imported goods become cheaper'), ('B', 'Imported goods become more expensive'),
          ('C', 'Exports become less competitive'), ('D', 'Nothing changes for trade')], 'B'),
        ('General Awareness', 'hard', '',
         'Two neighboring countries share a river. Country A builds a large dam upstream. Which outcome is most likely to create tension?',
         [('A', 'Country B gets more water than before'), ('B', 'Country A gets no benefit from the dam'),
          ('C', 'Reduced water flow reaching Country B downstream'), ('D', 'Both countries agree instantly on water sharing')], 'C'),

        ('Pattern & Code Reasoning', 'easy', '', 'What comes next: 2A, 4C, 6E, 8G, ___?',
         [('A', '9H'), ('B', '10I'), ('C', '10H'), ('D', '12I')], 'B'),
        # NOTE: source PDF text extraction for this item only preserved one
        # option ("A) DBOEMF — Answer: DBOEMF"), losing B/C/D. The correct
        # answer is derivable directly from the stated rule (each letter
        # shifted forward by one: C-A-N-D-L-E -> D-B-O-E-M-F), so it's kept
        # as option A with three single-letter-perturbed distractors added
        # to make it a well-formed 4-option question.
        ('Pattern & Code Reasoning', 'medium', '',
         'If FRIEND is written as GSJFOE (each letter shifted forward by one), how is CANDLE written?',
         [('A', 'DBOEMF'), ('B', 'DBOEMG'), ('C', 'DCOEMF'), ('D', 'DBPEMF')], 'A'),
        # NOTE: correct answer not explicitly marked in source; inferred
        # from the clear pattern (MAP/TAP/CAP all end in "-AP", MAT doesn't).
        ('Pattern & Code Reasoning', 'hard', '', 'Find the odd one out: MAP, TAP, CAP, MAT',
         [('A', 'MAP'), ('B', 'TAP'), ('C', 'CAP'), ('D', 'MAT')], 'D'),

        ('Verbal / Logical Reasoning', 'easy', '', 'Doctor is to Hospital as Teacher is to ___?',
         [('A', 'Classroom'), ('B', 'School'), ('C', 'Blackboard'), ('D', 'Homework')], 'B'),
        ('Verbal / Logical Reasoning', 'medium', '',
         'All licensed engineers have passed a certification exam. Riya is a licensed engineer. What can we conclude?',
         [('A', 'Riya designed the exam'), ('B', 'Riya has passed a certification exam'),
          ('C', 'Riya is the most senior engineer'), ('D', 'No conclusion is possible')], 'B'),
        ('Verbal / Logical Reasoning', 'hard', '',
         'No reptiles are mammals. All snakes are reptiles. Which must be true?',
         [('A', 'All snakes are mammals'), ('B', 'No snakes are mammals'),
          ('C', 'Some snakes are mammals'), ('D', 'No conclusion possible')], 'B'),
    ],

    'undergraduate': [
        ('Reading Comprehension', 'easy',
         "A startup pivots its product twice within its first year based on user feedback.",
         'What does this most likely indicate?',
         [('A', 'The founders are indecisive and directionless'), ('B', 'The team is responsive to market signals'),
          ('C', 'The product idea was bad from the start'), ('D', 'Pivoting always guarantees success')], 'B'),
        ('Reading Comprehension', 'medium',
         "Despite strong quarterly profits, a company's stock price fell after the earnings call.",
         "What's the most likely explanation?",
         [('A', 'The market ignores profits entirely'), ('B', 'Investor expectations were higher than actual results'),
          ('C', 'Profit and stock price are unrelated'), ('D', 'The report contained a math error')], 'B'),
        ('Reading Comprehension', 'hard',
         "A researcher's paper concludes 'X causes Y' based solely on a survey showing X and Y often occur together.",
         'What is the strongest critique of this conclusion?',
         [('A', 'Surveys are illegal'), ('B', "Correlation shown in a survey doesn't establish causation"),
          ('C', 'Y should have been studied instead'), ('D', 'The researcher should have used more colors in the chart')], 'B'),

        ('General Awareness', 'easy', '', 'Which of these is typically considered a "soft skill" in a workplace?',
         [('A', 'Coding in Python'), ('B', 'Communication'), ('C', 'Operating machinery'), ('D', 'Data entry speed')], 'B'),
        ('General Awareness', 'medium', '', 'A rise in interest rates set by a central bank generally aims to:',
         [('A', 'Encourage more borrowing'), ('B', 'Control inflation by discouraging excess borrowing'),
          ('C', 'Increase government spending directly'), ('D', 'Devalue the currency intentionally')], 'B'),
        ('General Awareness', 'hard', '',
         'A company outsources part of its production to cut costs, but faces backlash over labor conditions at the supplier. This illustrates a tension between:',
         [('A', 'Innovation and tradition'), ('B', 'Cost efficiency and ethical responsibility'),
          ('C', 'Marketing and sales'), ('D', 'Local and global taxation')], 'B'),

        ('Pattern & Code Reasoning', 'easy', '', 'What comes next: 3B, 6D, 9F, 12H, ___?',
         [('A', '14J'), ('B', '15J'), ('C', '15I'), ('D', '16J')], 'B'),
        ('Pattern & Code Reasoning', 'medium', '',
         'If TEACHER is coded as UFBDIFS (each letter shifted forward by one), how is STUDENT coded?',
         [('A', 'TUVEOFU'), ('B', 'TUVEOFT'), ('C', 'SUVEOFU'), ('D', 'TUWEOFU')], 'A'),
        ('Pattern & Code Reasoning', 'hard', '', 'Find the odd one out: Democracy, Monarchy, Oligarchy, Philosophy',
         [('A', 'Democracy'), ('B', 'Monarchy'), ('C', 'Oligarchy'), ('D', 'Philosophy')], 'D'),

        ('Verbal / Logical Reasoning', 'easy', '', 'Author is to Book as Architect is to ___?',
         [('A', 'Blueprint'), ('B', 'Building'), ('C', 'Construction'), ('D', 'City')], 'B'),
        ('Verbal / Logical Reasoning', 'medium', '',
         'All patented inventions must be novel. This invention is patented. What can we conclude?',
         [('A', 'This invention is expensive'), ('B', 'This invention is novel'),
          ('C', 'This invention will succeed commercially'), ('D', 'No conclusion is possible')], 'B'),
        ('Verbal / Logical Reasoning', 'hard', '',
         'All successful negotiations require compromise. This negotiation involved no compromise. What can we conclude?',
         [('A', 'This negotiation took a long time'), ('B', 'This negotiation was not successful'),
          ('C', 'This negotiation was successful'), ('D', 'No conclusion is possible')], 'B'),
    ],

    'postgraduate': [
        ('Reading Comprehension', 'easy',
         "A manager delegates a high-visibility project to a junior employee instead of a senior one, "
         "citing the junior's fresh perspective.",
         'What does this best illustrate?',
         [('A', "The manager doesn't trust senior staff"), ('B', 'A deliberate choice prioritizing a specific strength over seniority'),
          ('C', 'The senior employee was unavailable'), ('D', 'Junior employees are always better')], 'B'),
        ('Reading Comprehension', 'medium',
         "A peer-reviewed paper is retracted after other labs fail to replicate its central finding.",
         'What does this best demonstrate?',
         [('A', 'Peer review is worthless'), ('B', 'The scientific process self-correcting through replication'),
          ('C', 'The original researchers committed fraud'), ('D', 'Retraction means the topic was unimportant')], 'B'),
        ('Reading Comprehension', 'hard',
         "An organization adopts a policy shown to work well in one country, without adapting it to local context, and it fails there.",
         'What principle does this best illustrate?',
         [('A', 'Best practices always transfer directly'), ('B', 'Context matters when transferring solutions across settings'),
          ('C', 'Policies never work anywhere'), ('D', 'Failure means the original policy was flawed')], 'B'),

        ('General Awareness', 'easy', '', 'In project management, "scope creep" refers to:',
         [('A', "Reducing a project's budget"), ('B', "Uncontrolled expansion of a project's requirements over time"),
          ('C', 'Finishing a project early'), ('D', 'A type of software bug')], 'B'),
        ('General Awareness', 'medium', '',
         "A firm's decision to prioritize short-term shareholder returns over long-term R&D investment illustrates a tradeoff between:",
         [('A', 'Legal and illegal practices'), ('B', 'Short-term gains and long-term sustainability'),
          ('C', 'Marketing and HR'), ('D', 'Domestic and international policy')], 'B'),
        ('General Awareness', 'hard', '',
         'Two departments both claim ownership of a shrinking budget. Which approach is most likely to resolve this constructively?',
         [('A', 'Ignoring the conflict'), ('B', 'A structured negotiation based on shared organizational priorities'),
          ('C', 'Letting the more senior department win by default'), ('D', 'Escalating publicly to force a decision')], 'B'),

        ('Pattern & Code Reasoning', 'easy', '', 'What comes next: 3D, 6H, 9L, 12P, ___?',
         [('A', '15S'), ('B', '15T'), ('C', '14T'), ('D', '16T')], 'B'),
        ('Pattern & Code Reasoning', 'medium', '',
         'If ANALYSIS is coded as BOBMZTJT (each letter shifted forward by one), how is SYNTHESIS coded?',
         [('A', 'TZOUIFTJT'), ('B', 'TZOUIFSJT'), ('C', 'TZOUHFTJT'), ('D', 'SZOUIFTJT')], 'A'),
        ('Pattern & Code Reasoning', 'hard', '', 'Find the odd one out: Correlation, Causation, Regression, Symphony',
         [('A', 'Correlation'), ('B', 'Causation'), ('C', 'Regression'), ('D', 'Symphony')], 'D'),

        ('Verbal / Logical Reasoning', 'easy', '', 'Hypothesis is to Experiment as Theory is to ___?',
         [('A', 'Evidence'), ('B', 'Guess'), ('C', 'Question'), ('D', 'Fiction')], 'A'),
        ('Verbal / Logical Reasoning', 'medium', '',
         'All peer-reviewed studies undergo external review. This study is peer-reviewed. What can we conclude?',
         [('A', 'This study is definitely correct'), ('B', 'This study underwent external review'),
          ('C', 'This study is widely cited'), ('D', 'No conclusion is possible')], 'B'),
        ('Verbal / Logical Reasoning', 'hard', '',
         'Every valid scientific theory must be falsifiable. Theory X cannot be falsified by any conceivable experiment. What can we conclude about Theory X?',
         [('A', 'Theory X is definitely false'), ('B', 'Theory X is not a valid scientific theory'),
          ('C', 'Theory X is unimportant'), ('D', 'No conclusion is possible')], 'B'),
    ],
}

# Learning Style Probes — 3 per tier, non-adaptive, tag mapping fixed:
# A=Visual, B=Reading/Verbal, C=Practical/Kinesthetic, D=Reasoning/Theoretical
LEARNING_STYLE_PROBES_BY_TIER = {
    'grade_8_10': [
        ('When learning a new concept, I understand it best when I:',
         ['See a diagram or graph of it', 'Read a step-by-step written explanation',
          'Work through a real example myself', 'Think about why it works before using it']),
        ('When I get stuck on a problem, I usually:',
         ['Look for a visual pattern', 'Re-read the question carefully',
          'Try different things until something works', 'Pause and think through the underlying logic']),
        ('I remember what I study best through:',
         ['Charts and color-coding', 'Notes and written definitions',
          'Practice and doing', 'Working out the reasoning myself before checking answers']),
    ],
    'grade_10_12': [
        ('When my teacher introduces a new idea, I grasp it fastest when:',
         ["It's shown as a graph, diagram, or visual", "It's explained in words step by step",
          'I try it out myself right away', 'I first understand why it makes sense']),
        ('For a school project, I prefer to:',
         ['Build a chart, diagram, or infographic', 'Write it up as a structured report',
          'Build or demo something hands-on', 'Research and reason through the underlying idea deeply']),
        ('Before an exam, my most effective revision method is:',
         ['Reviewing color-coded notes or mind maps', 'Re-reading my written notes',
          'Practicing as much as possible', 'Talking myself through the logic of each topic']),
    ],
    'undergraduate': [
        ('When tackling a new topic in a course, I learn fastest by:',
         ['Watching a diagram-heavy or visual explanation', 'Reading the material closely',
          'Doing the practice work immediately', 'Understanding the theory or rationale before applying it']),
        ('For a group assignment, I contribute best by:',
         ['Building visuals or slides', 'Writing up the analysis',
          'Prototyping or doing the hands-on work', 'Framing the argument or strategy']),
        ('When I revisit old material to refresh it, I prefer to:',
         ['Skim diagrams or summaries', 'Re-read my notes in full',
          'Re-do a few practice exercises', 'Reconstruct the reasoning from first principles']),
    ],
    'postgraduate': [
        ('When engaging with a new theoretical framework, I absorb it fastest by:',
         ['Mapping it visually (diagram or model)', 'Reading the original source material closely',
          'Applying it to a live case or dataset immediately', 'Interrogating its assumptions and limits first']),
        ('In a research or project team, I add the most value by:',
         ['Building visual models or dashboards', 'Writing the analysis or report',
          'Running the experiments or analysis hands-on', 'Framing the research question and critique']),
        ('When preparing to present findings, I prepare best by:',
         ['Building charts or visuals first', 'Writing a full script or narrative',
          'Rehearsing with the actual data live', 'Thinking through likely counter-arguments first']),
    ],
}


# ============================================================ PART 2 =======
# Shared across all tiers unless `tiers` is set.

PERSONALITY_QUESTIONS = [
    ('When starting a new project or assignment, I usually:', [
        ('A', 'Set clear goals and track progress until it’s done', 'Achiever'),
        ('B', 'Look for a new or different way to approach it', 'Explorer'),
        ('C', 'Prefer to work with others and share ideas', 'Collaborator'),
        ('D', 'Research thoroughly before starting', 'Analyst'),
    ]),
    ('I feel most satisfied when:', [
        ('A', 'I complete a task and see the result', 'Achiever'),
        ('B', 'I discover something new or unexpected', 'Explorer'),
        ('C', 'A team succeeds together', 'Collaborator'),
        ('D', 'I fully understand how or why something works', 'Analyst'),
    ]),
    ('If a plan doesn’t work, I tend to:', [
        ('A', 'Push harder and reach the goal a different way', 'Achiever'),
        ('B', 'Try a completely new approach', 'Explorer'),
        ('C', 'Ask others for input or help', 'Collaborator'),
        ('D', 'Step back and analyze what went wrong first', 'Analyst'),
    ]),
]

INTERESTS_QUESTIONS_SHARED = [
    ('Which activity would you enjoy most?', [
        ('A', 'Solving a tricky puzzle or problem', 'STEM/Analytical'),
        ('B', 'Designing, writing, or creating something original', 'Creative/Artistic'),
        ('C', 'Helping, teaching, or organizing a group of people', 'People/Social'),
        ('D', 'Planning a project or pitching an idea', 'Business/Leadership'),
    ]),
    ('In free time, I’m most drawn to:', [
        ('A', 'Science, technology, or how things work', 'STEM/Analytical'),
        ('B', 'Art, music, writing, or design', 'Creative/Artistic'),
        ('C', 'Volunteering, mentoring, or community activities', 'People/Social'),
        ('D', 'Starting projects, competitions, or ventures', 'Business/Leadership'),
    ]),
]

# Q3 wording variants
INTERESTS_Q3_SCHOOL = (
    'If you could pick one elective to explore deeply, it would be:',
    [
        ('A', 'Math / Science / Computer Science', 'STEM/Analytical'),
        ('B', 'Art / Music / Literature', 'Creative/Artistic'),
        ('C', 'Psychology / Social Studies / Languages', 'People/Social'),
        ('D', 'Economics / Business Studies', 'Business/Leadership'),
    ],
    ['grade_8_10', 'grade_10_12'],
)
INTERESTS_Q3_UGPG = (
    'Which career field appeals to you most right now?',
    [
        ('A', 'Engineering / Data / Research', 'STEM/Analytical'),
        ('B', 'Design / Media / Content', 'Creative/Artistic'),
        ('C', 'Education / Healthcare / Social Work', 'People/Social'),
        ('D', 'Business / Management / Entrepreneurship', 'Business/Leadership'),
    ],
    ['undergraduate', 'postgraduate'],
)

WELLBEING_QUESTIONS = [
    ('confidence', 'How confident do you feel about keeping up with your coursework right now?',
     ['Very confident', 'Somewhat confident', 'Somewhat worried', 'Very worried']),
    ('motivation', 'How motivated do you feel about your studies at the moment?',
     ['Very motivated', 'Somewhat motivated', 'Low motivation', 'Struggling to stay motivated']),
    ('workload', 'How manageable does your current workload/stress feel?',
     ['Very manageable', 'Mostly manageable', 'Often overwhelming', 'Constantly overwhelming']),
]

SOFT_SKILLS_QUESTIONS = [
    ('group_role', 'When working on a group task, I usually:', [
        ('A', 'Take the lead and organize the group', 'Leadership-leaning'),
        ('B', 'Focus on getting my part done well', 'Independent/Reliable'),
        ('C', 'Help resolve disagreements and keep the group positive', 'Collaborative'),
        ('D', 'Prefer contributing ideas over managing logistics', 'Idea-generator'),
    ]),
    ('deadlines', 'My approach to deadlines is usually:', [
        ('A', 'I plan ahead and finish early', 'Strong time-management'),
        ('B', 'I work steadily and finish on time', 'Moderate time-management'),
        ('C', 'I tend to do most of it close to the deadline', 'Needs pacing support'),
        ('D', 'I often need reminders or extensions', 'Needs organization support'),
    ]),
    ('conflict', 'When I disagree with someone in a group, I usually:', [
        ('A', 'State my view clearly and try to persuade them', 'Assertive'),
        ('B', 'Listen first, then share my perspective', 'Diplomatic'),
        ('C', 'Go along with the group to avoid conflict', 'Accommodating'),
        ('D', 'Avoid the discussion if possible', 'Conflict-avoidant'),
    ]),
]

OPEN_MESSAGE_QUESTION = (
    "Is there anything you'd like your teacher to know about you — a challenge you're facing, "
    "something you're proud of, or how you learn best?"
)
