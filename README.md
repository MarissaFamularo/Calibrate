# Calibrate

A proposed clinical simulation tool to help residents calibrate their trust in AI recommendations.

## Concept

Calibrate is a Meta hackathon project in pre-development. It aims to help residents accept appropriate AI recommendations while recognizing when to question or override incorrect ones. The educational goal is to address both overreliance on AI and reflexive dismissal of useful recommendations.

## Proposed workflow

1. A resident works through a text-first, synthetic patient scenario.
2. At defined scenario states, a simulated assistant presents controlled, scripted recommendations that may be correct or incorrect.
3. The resident accepts, questions, or overrides the recommendation and explains their reasoning.
4. Educator feedback reviews the decision, including missed errors and inappropriate rejection of sound advice.
5. A simple session-level assessment summarizes the resident's responses across the cases.

## Scoped MVP

- A few reproducible, text-first synthetic patient cases.
- Scripted correct and incorrect assistant suggestions at predefined states.
- Resident decisions and brief reasoning captured during each case.
- Educator feedback on both overreliance and reflexive dismissal.
- A simple session-level assessment.

Voice interaction, longitudinal tracking, and adaptive scenarios are possible later extensions and are outside the initial MVP.

## Intended Modal use

The tentative architecture would use Modal for a Python simulation backend and parallel evaluation jobs to check reproducible scenarios and scripted recommendation behavior. This is a proposed use for a Modal credit application. No Modal integration or infrastructure has been implemented or deployed, and the architecture may change during development.

## Current status

This project currently contains only this concept README. There is no application implementation, runnable prototype, or deployed integration. Educational efficacy has not been established.

## Educational scope

Calibrate is intended for education using synthetic cases only. It is not intended for clinical care, real patient decision-making, or use with identifiable patient information.
