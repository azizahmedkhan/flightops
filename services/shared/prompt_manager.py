"""
Centralized prompt management for FlightOps Copilot services.
All LLM prompts are defined here and can be referenced by any service.
"""

from typing import Dict, Any, Optional
import json


class PromptManager:
    """Centralized prompt management system."""
    
    # Agent Service Prompts
    REBOOKING_OPTIMIZATION = """
Optimize these airline rebooking options based on passenger profiles and flight context:

Flight: {flight_no} from {origin} to {destination}
Impact: {impact_summary}
Passenger Profiles: {passenger_count} passengers, {vip_count} VIP

Current Options:
{options_json}

Optimize by:
1. Adjusting customer experience scores based on passenger preferences
2. Refining cost estimates based on passenger mix
3. Improving success probabilities based on historical data
4. Adding personalized recommendations
5. Ranking by overall value (CX score vs cost)

IMPORTANT: Return ONLY a valid JSON array with the optimized options. Do not include any explanations, markdown formatting, or additional text. The response must be parseable JSON.
"""

    # Communications Service Prompts
    TONE_REWRITE = """Rewrite this airline communication to be more {tone} while keeping all factual information intact:

{template_text}

Make it sound more {tone} but keep the same structure and all details."""

    TRANSLATION = """Translate this airline communication to {target_language} with appropriate cultural adaptation:

Original text:
{text}

Context:
- Flight: {flight_no}
- Issue: {issue}
- Customer: {customer_name}

Cultural considerations for {target_language}:
{cultural_context}

Requirements:
1. Maintain professional airline tone
2. Adapt to cultural communication style
3. Keep all factual information accurate
4. Use appropriate formality level
5. Include relevant cultural references if appropriate

Return only the translated text."""

    SENTIMENT_ANALYSIS = """Analyze the sentiment of this customer communication:

{text}

{context_str}

Provide:
1. Sentiment (positive/neutral/negative)
2. Sentiment score (-1.0 to 1.0)
3. Key emotions detected (list)
4. Urgency level (low/medium/high)
5. Recommended response tone (empathetic/professional/urgent)
6. Key concerns (list)

Format as JSON."""

    # Predictive Service Prompts
    DISRUPTION_PREDICTION = """
Analyze this flight operation data and predict potential disruptions:

Flight: {flight_no} on {date}
Route: {origin} to {destination}

Weather at origin: {weather_data}
Crew analysis: {crew_analysis}
Aircraft status: {aircraft_analysis}
Historical patterns: {historical_data}

Provide:
1. Risk level (low/medium/high/critical)
2. Risk score (0.0-1.0)
3. Most likely disruption type
4. Confidence level (0.0-1.0)
5. Key risk factors (list)
6. Recommendations (list)

Format as JSON.
"""

    # Crew Service Prompts
    CREW_ANALYSIS = """
Analyze this crew situation for airline operations:

Disruption Context: {disruption_context}
Crew Data: {crew_data_json}

Provide:
1. Risk assessment (low/medium/high)
2. Key concerns (list)
3. Recommended actions (list)
4. Priority level (1-5)
5. Estimated resolution time

Format as JSON.
"""

    # Test Prompts
    TEST_JOKE_FACT = """
Give me a quick and funny time-of-day joke or quirky fact that's different each time.

Make it:
- Light-hearted and entertaining
- Related to the current time of day if possible
- Different from previous responses
- Brief (1-2 sentences)
- Appropriate for a professional airline environment

Just provide the joke or fact directly, no additional formatting.
"""

    @classmethod
    def get_prompt(cls, prompt_name: str, **kwargs) -> str:
        """
        Get a formatted prompt by name.
        
        Args:
            prompt_name: Name of the prompt (e.g., 'REBOOKING_OPTIMIZATION')
            **kwargs: Variables to format into the prompt
            
        Returns:
            Formatted prompt string
            
        Raises:
            ValueError: If prompt_name is not found
        """
        prompt_template = getattr(cls, prompt_name, None)
        if prompt_template is None:
            raise ValueError(f"Prompt '{prompt_name}' not found")
        
        return prompt_template.format(**kwargs)

    @classmethod
    def get_rebooking_optimization_prompt(cls, flight: Dict[str, Any], impact: Dict[str, Any], 
                                        passenger_profiles: list, options: list) -> str:
        """Get formatted rebooking optimization prompt."""
        vip_count = len([p for p in passenger_profiles if p.get('loyalty_tier') in ['Gold', 'Platinum']])
        
        return cls.get_prompt(
            'REBOOKING_OPTIMIZATION',
            flight_no=flight.get('flight_no', 'Unknown'),
            origin=flight.get('origin', 'Unknown'),
            destination=flight.get('destination', 'Unknown'),
            impact_summary=impact.get('summary', 'Unknown impact'),
            passenger_count=len(passenger_profiles),
            vip_count=vip_count,
            options_json=json.dumps(options, indent=2)
        )

    @classmethod
    def get_tone_rewrite_prompt(cls, template_text: str, tone: str) -> str:
        """Get formatted tone rewrite prompt."""
        return cls.get_prompt(
            'TONE_REWRITE',
            template_text=template_text,
            tone=tone
        )

    @classmethod
    def get_translation_prompt(cls, text: str, target_language: str, context: Dict[str, Any], 
                             cultural_context: str) -> str:
        """Get formatted translation prompt."""
        return cls.get_prompt(
            'TRANSLATION',
            text=text,
            target_language=target_language,
            flight_no=context.get('flight_no', 'Unknown'),
            issue=context.get('issue', 'operational delay'),
            customer_name=context.get('customer_name', 'Valued Customer'),
            cultural_context=cultural_context
        )

    @classmethod
    def get_sentiment_analysis_prompt(cls, text: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Get formatted sentiment analysis prompt."""
        context_str = ""
        if context:
            context_str = f"Context: Flight {context.get('flight_no', 'Unknown')}, Issue: {context.get('issue', 'Unknown')}"
        
        return cls.get_prompt(
            'SENTIMENT_ANALYSIS',
            text=text,
            context_str=context_str
        )

    @classmethod
    def get_disruption_prediction_prompt(cls, flight_data: Dict[str, Any], weather_data: Dict[str, Any],
                                       crew_analysis: Dict[str, Any], aircraft_analysis: Dict[str, Any],
                                       historical_data: Dict[str, Any]) -> str:
        """Get formatted disruption prediction prompt."""
        return cls.get_prompt(
            'DISRUPTION_PREDICTION',
            flight_no=flight_data.get('flight_no', 'Unknown'),
            date=flight_data.get('date', 'Unknown'),
            origin=flight_data.get('origin', 'Unknown'),
            destination=flight_data.get('destination', 'Unknown'),
            weather_data=weather_data,
            crew_analysis=crew_analysis,
            aircraft_analysis=aircraft_analysis,
            historical_data=historical_data
        )

    @classmethod
    def get_crew_analysis_prompt(cls, crew_data: Dict[str, Any], disruption_context: str) -> str:
        """Get formatted crew analysis prompt."""
        return cls.get_prompt(
            'CREW_ANALYSIS',
            disruption_context=disruption_context,
            crew_data_json=json.dumps(crew_data, indent=2)
        )

    @classmethod
    def get_test_joke_fact_prompt(cls) -> str:
        """Get test joke/fact prompt."""
        return cls.get_prompt('TEST_JOKE_FACT')

    @classmethod
    def list_prompts(cls) -> Dict[str, str]:
        """List all available prompts with their descriptions."""
        return {
            'REBOOKING_OPTIMIZATION': 'Optimize airline rebooking options based on passenger profiles',
            'TONE_REWRITE': 'Rewrite airline communications to match specific tone',
            'TRANSLATION': 'Translate communications with cultural adaptation',
            'SENTIMENT_ANALYSIS': 'Analyze customer communication sentiment',
            'DISRUPTION_PREDICTION': 'Predict potential flight disruptions',
            'CREW_ANALYSIS': 'Analyze crew situations during disruptions',
            'TEST_JOKE_FACT': 'Generate time-of-day jokes or quirky facts for testing'
        }

    @classmethod
    def get_prompt_metadata(cls) -> Dict[str, Dict[str, Any]]:
        """Get metadata about each prompt including model settings."""
        return {
            'REBOOKING_OPTIMIZATION': {
                'service': 'agent-svc',
                'temperature': 0.3,
                'response_format': 'JSON',
                'description': 'Optimize airline rebooking options based on passenger profiles'
            },
            'TONE_REWRITE': {
                'service': 'comms-svc',
                'temperature': 0.7,
                'response_format': 'Plain Text',
                'description': 'Rewrite airline communications to match specific tone'
            },
            'TRANSLATION': {
                'service': 'comms-svc',
                'temperature': 0.3,
                'response_format': 'Plain Text',
                'description': 'Translate communications with cultural adaptation'
            },
            'SENTIMENT_ANALYSIS': {
                'service': 'comms-svc',
                'temperature': 0.3,
                'response_format': 'JSON',
                'description': 'Analyze customer communication sentiment'
            },
            'DISRUPTION_PREDICTION': {
                'service': 'predictive-svc',
                'temperature': 0.3,
                'response_format': 'JSON',
                'description': 'Predict potential flight disruptions'
            },
            'CREW_ANALYSIS': {
                'service': 'crew-svc',
                'temperature': 0.3,
                'response_format': 'JSON',
                'description': 'Analyze crew situations during disruptions'
            },
            'TEST_JOKE_FACT': {
                'service': 'agent-svc',
                'temperature': 0.8,
                'response_format': 'Plain Text',
                'description': 'Generate time-of-day jokes or quirky facts for testing'
            }
        }
