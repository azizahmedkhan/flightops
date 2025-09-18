# Customer Questions Library

This document contains a comprehensive list of questions that customers can choose from when interacting with the FlightOps system.

## Flight Impact Questions

### Basic Impact Assessment
1. "What is the impact of the delay on [flight_number] on [date]?"
2. "How many passengers are affected by the disruption on [flight_number]?"
3. "What is the crew impact for [flight_number] on [date]?"
4. "What is the current status of [flight_number] on [date]?"

### Detailed Impact Analysis
5. "How many passengers have connecting flights on [flight_number]?"
6. "What is the aircraft status for [flight_number] on [date]?"
7. "What are the crew roles and duty hours for [flight_number]?"
8. "What is the passenger breakdown by loyalty tier for [flight_number]?"

## Rebooking and Recovery Questions

### Rebooking Options
9. "What are the rebooking options for [flight_number] on [date]?"
10. "What is the best rebooking strategy for [flight_number] passengers?"
11. "Can we accommodate all passengers on alternative flights?"
12. "What are the cost implications of different rebooking options?"

### Recovery Planning
13. "What is the estimated recovery time for [flight_number]?"
14. "How can we minimize passenger inconvenience for [flight_number]?"
15. "What compensation options are available for [flight_number] passengers?"
16. "What are the alternative routing options for [flight_number]?"

## Communication Questions

### Customer Communication
17. "Draft email and SMS notifications for [flight_number] passengers"
18. "What should we tell passengers about the delay on [flight_number]?"
19. "Generate customer communication for weather-related delay on [flight_number]"
20. "Create passenger update for mechanical issue on [flight_number]"

### Internal Communication
21. "Draft internal briefing for [flight_number] disruption"
22. "What updates should we send to crew for [flight_number]?"
23. "Generate operational summary for [flight_number] management"

## Policy and Compliance Questions

### Policy Reference
24. "What is our policy for weather-related delays on [flight_number]?"
25. "What compensation is required for [flight_number] passengers?"
26. "What are our obligations for connecting passengers on [flight_number]?"
27. "What is the policy for crew duty time limits on [flight_number]?"

### Regulatory Compliance
28. "What regulatory requirements apply to [flight_number] delay?"
29. "What documentation is needed for [flight_number] disruption?"
30. "What are the safety requirements for [flight_number] recovery?"

## Operational Questions

### Resource Management
31. "What crew resources are available for [flight_number] recovery?"
32. "What aircraft are available for [flight_number] rebooking?"
33. "What ground support is needed for [flight_number]?"
34. "What maintenance issues affect [flight_number]?"

### Weather and External Factors
35. "What weather conditions are affecting [flight_number]?"
36. "What external factors are causing [flight_number] delay?"
37. "What is the forecast for [flight_number] route?"
38. "What air traffic control issues affect [flight_number]?"

## Financial Impact Questions

### Cost Analysis
39. "What is the financial impact of [flight_number] delay?"
40. "What are the compensation costs for [flight_number] passengers?"
41. "What are the operational costs for [flight_number] recovery?"
42. "What is the revenue impact of [flight_number] cancellation?"

## Customer Service Questions

### Passenger Experience
43. "How can we improve passenger experience during [flight_number] delay?"
44. "What amenities should we provide for [flight_number] passengers?"
45. "How can we handle special needs passengers on [flight_number]?"
46. "What is the best way to communicate with [flight_number] passengers?"

## Emergency and Crisis Management

### Crisis Response
47. "What is our emergency response plan for [flight_number]?"
48. "How should we handle media inquiries about [flight_number]?"
49. "What is the escalation process for [flight_number] issues?"
50. "How do we coordinate with other airlines for [flight_number] recovery?"

## Quick Action Templates

### Common Scenarios
- **Weather Delay**: "What is the impact and recovery plan for [flight_number] delayed due to weather?"
- **Mechanical Issue**: "What are the options for [flight_number] with mechanical problems?"
- **Crew Shortage**: "How do we handle [flight_number] with crew availability issues?"
- **Air Traffic Delay**: "What is the impact of ATC delays on [flight_number]?"
- **Passenger Disruption**: "How do we handle passenger issues on [flight_number]?"

## Usage Instructions

1. Replace `[flight_number]` with the actual flight number (e.g., "NZ123")
2. Replace `[date]` with the actual date (e.g., "2025-09-17")
3. Questions can be customized by adding specific details
4. Multiple questions can be combined for comprehensive analysis
5. Questions are designed to work with the existing tool functions in the agent service

## Integration Notes

- Questions are designed to work with the existing `/ask` endpoint
- All questions require `flight_no` and `date` parameters
- Questions trigger appropriate tool functions automatically
- Results include policy citations and grounded responses
