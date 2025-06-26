"""LLM prompts for filter creation and management"""

FILTER_CREATION_PROMPT = """Convert the given text into a structured filter configuration.
Output only valid JSON matching this structure:
{
    "filter_text": str,  // The text/concept to filter
    "filter_type": str,  // topic|concept|entity|category|emotion|complex
    "content_type": str,  // text|image|all
    "intensity": int,    // 1-5
    "filter_metadata": {
        "context": str,
        "related_terms": list[str],
        "category_specific": dict
    },
    "is_temporary": bool,
    "duration": str      // null|"1 day"|"1 week"|"1 month"
}"""

FILTER_EVALUATION_PROMPT = """Analyze if content matches any of the given filters.
Consider contextual meaning, implications, and related concepts.
Return matched filter indices and confidence scores in a JSON object. Follow the format exactly as shown below.

Example:
Content: "The administration's new economic policy has led to protests"
Filters: [
    {"filter_text": "politics", "filter_metadata": {"context": "political news"}},
    {"filter_text": "economic policy", "filter_metadata": {"context": "finance"}},
    {"filter_text": "protests", "filter_metadata": {"context": "civil unrest"}}
]

For this example, should match all three filters with different confidence. 
The content is a Strong political content (Filter 0),
The content also has direct mention of economic policy (Filter 1),
Finally, Protests mentioned but not detailed (Filter 2).
So, the JSON output will be:
{
    "matched_filter_ids": [0, 1, 2],
    "confidence_scores": {
        "0": 0.85,  
        "1": 0.90,  
        "2": 0.70,
    }
}
"""

LOW_INTENSITY_PROMPT = """For the given content that may contain [TITLE] and [BODY] sections,
identify specific words or phrases that match the given filters.
Return a list of exact text segments that should be modified, one per line.
Do not add any markers or formatting - just return the raw text segments.
Preserve all [TITLE] and [BODY] tags exactly as they appear."""

MEDIUM_INTENSITY_PROMPT = """
You are given two things: 
1) a content that may contain [TITLE] and [BODY] sections,
2) a list of filters with their corresponding sensitive topics.

Your Job: Create a brief warning message (under 100 characters) about this sensitive content.
Return only the warning message without any formatting or markers.

Must follow these guidelines:
Preserve all [TITLE] and [BODY] tags and their ending [/TITLE] and [/BODY] exactly as they appear.
Try to make sure that the lenght of the warning is not more than the title ( title is the text content within [Title] and [/Title] tags.)
Try to give a personalized tone, because the warning is crafted for this particular user.
Also, in the warning message, DO NOT specifically mention the filter topics, because thats the thing they want to filter/avoid.
"""

HIGH_INTENSITY_PROMPT = """For the given content that may contain [TITLE] and [BODY] sections,
rewrite the content to remove or neutralize sensitive topics only related to the filters shared below. 
But, preserving the general meaning.
Return only the rewritten text without any formatting or markers.
Preserve all [TITLE] and [BODY] tags and their ending [/TITLE] and [/BODY] exactly as they appear. 
Only rewrite their corresponding content."""



AGGRESSIVE_MODE_PROMPT = """For the given content that may contain [TITLE] and [BODY] sections,
aggressively rewrite the content to fully remove or neutralize all sensitive topics.
Consider all filters together for a comprehensive rewrite.
Return only the rewritten text without any formatting or markers.
Preserve all [TITLE] and [BODY] tags exactly as they appear.
Keep sections between [TITLE] and [BODY] tags intact and only rewrite their content."""

CONVERSATION_COMPLETE = {
    "text": "Your filter has been saved. Would you like to add another?",
    "type": "complete",
    "options": ["Add another filter", "I'm done"]
}