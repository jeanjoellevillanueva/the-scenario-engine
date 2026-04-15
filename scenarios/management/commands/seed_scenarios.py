from textwrap import dedent

from django.core.management.base import BaseCommand

from scenarios.models import LearningObjective
from scenarios.models import Scenario


class Command(BaseCommand):
    """Seed the database with the test scenario."""

    help = "Seed the database with the Dave/Duchess veterinary scenario"

    def handle(self, *args, **options):
        """Execute the command."""
        scenario, created = Scenario.objects.update_or_create(
            name="Duchess the Sick Cow",
            defaults={
                "persona": dedent('''
                    You are Dave, a farmer in his 50s who lives on a remote property
                    outside Armidale, NSW, Australia. You're worried about your prize
                    Hereford cow, Duchess.

                    Personality traits:
                    - Helpful but not medically precise - you describe what you see in
                      plain language
                    - Get a bit anxious if the student seems unsure or hesitant
                    - Occasionally throw in irrelevant details about your other cattle,
                      the weather, or farm life
                    - You're a farmer, not a vet - use colloquial Australian expressions
                      like "off her tucker" (not eating), "arvo" (afternoon), "reckon",
                      "mate"
                    - You genuinely care about Duchess - she's valuable and you're fond
                      of her

                    What you know about Duchess:
                    - She's been off her feed since Tuesday afternoon (3 days ago)
                    - She's lethargic and standing apart from the herd
                    - Her manure has been looser than normal
                    - You noticed her drooling a bit yesterday
                    - Temperature felt warm when you checked her ears
                    - She's been in the bottom paddock near the creek
                    - There are some wilted cherry tree branches that blew down in last
                      week's storm
                    - No other cattle are showing symptoms
                    - She's 4 years old, had a calf 6 months ago (weaned now)
                    - You changed to a new hay supplier 2 weeks ago
                ''').strip(),
                "setting": dedent('''
                    A remote cattle property 45 minutes outside Armidale, NSW, Australia.
                    It's late autumn, and there was a storm last week that brought down
                    some tree branches. The property has several paddocks, a creek running
                    through the bottom paddock, and mixed pasture with some native trees
                    including cherry trees along the fence lines.
                ''').strip(),
                "context": dedent('''
                    A final-year veterinary science student has been called out to Dave's
                    property because his prize Hereford cow, Duchess, isn't right. She's
                    off her feed, lethargic, and Dave's worried. The student needs to
                    gather information from Dave, perform a systematic assessment through
                    questioning, consider environmental factors, identify possible
                    diagnoses, and recommend a treatment plan.

                    This is a learning simulation where the student must demonstrate
                    clinical reasoning skills by asking the right questions and arriving
                    at reasonable differential diagnoses.
                ''').strip(),
                "evaluation_criteria": {
                    "passing_score": 3,
                    "max_score": 5,
                    "criteria": [
                        "Systematic approach to history gathering",
                        "Consideration of multiple body systems",
                        "Environmental awareness",
                        "Sound clinical reasoning",
                        "Appropriate treatment recommendations",
                    ],
                },
                "is_active": True,
            },
        )

        if created:
            self.stdout.write(self.style.SUCCESS(f"Created scenario: {scenario.name}"))
        else:
            self.stdout.write(self.style.WARNING(f"Updated scenario: {scenario.name}"))

        objectives_data = [
            {
                "objective_id": "LO1",
                "description": "Gather relevant history (feeding, water intake, diet changes, symptom timeline)",
                "detection_hints": dedent('''
                    Student asks about: when symptoms started, feeding behavior, water
                    intake, recent diet or feed changes, timeline of symptoms, previous
                    health issues
                ''').strip(),
            },
            {
                "objective_id": "LO2",
                "description": "Perform systematic assessment (temperature, gait, manure, respiratory rate)",
                "detection_hints": dedent('''
                    Student inquires about: body temperature, how she's walking/moving,
                    manure consistency, breathing rate, heart rate, hydration status,
                    rumen sounds, eye/nose discharge
                ''').strip(),
            },
            {
                "objective_id": "LO3",
                "description": "Consider environmental factors (pasture type, toxic plants, weather, sick animals)",
                "detection_hints": dedent('''
                    Student asks about: where cattle have been grazing, any toxic plants
                    in paddocks, recent weather events, other sick animals in herd,
                    new introductions to herd, access to unusual substances
                ''').strip(),
            },
            {
                "objective_id": "LO4",
                "description": "Identify at least two differential diagnoses",
                "detection_hints": dedent('''
                    Student proposes multiple possible diagnoses based on gathered
                    information. Good differentials might include: plant toxicity
                    (cherry/cyanide), acidosis from feed change, infection, hardware
                    disease, etc.
                ''').strip(),
            },
            {
                "objective_id": "LO5",
                "description": "Recommend a treatment plan with reasoning and follow-up",
                "detection_hints": dedent('''
                    Student provides treatment recommendations with clear reasoning,
                    explains why they chose this approach, includes follow-up plan,
                    discusses when to escalate or seek further care
                ''').strip(),
            },
        ]

        for obj_data in objectives_data:
            obj, obj_created = LearningObjective.objects.update_or_create(
                scenario=scenario,
                objective_id=obj_data["objective_id"],
                defaults={
                    "description": obj_data["description"],
                    "detection_hints": obj_data["detection_hints"],
                    "is_active": True,
                },
            )
            action = "Created" if obj_created else "Updated"
            self.stdout.write(f"  {action} objective: {obj.objective_id}")

        self.stdout.write(
            self.style.SUCCESS("\nScenario seeding complete!")
        )
