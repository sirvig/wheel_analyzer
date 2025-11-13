---
allowed-tools: Read, Grep, Glob, TodoWrite, AskUserQuestion, Edit, Write, Bash, Task
description: Process pending tasks from a reference file one at a time
argument-hint: [path to reference file]
model: sonnet
---

# process-tasks

This command reads a specified reference file containing pending tasks and systematically works through them one at a time. It validates input, plans the work, asks clarifying questions when needed, and implements changes with proper testing and documentation updates. See the `Instructions` section below for the complete workflow.

## Variables

REFERENCE_FILE: $1

## Instructions

- **Step 1: Validate Input**
  - Check if REFERENCE_FILE ($1) was provided
  - If not provided, use AskUserQuestion tool to prompt the user for the file path
  - Validate that the file exists using Read tool
  - If file doesn't exist, inform the user and request a valid path

- **Step 2: Read and Parse Reference File**
  - Use Read tool to load the complete contents of REFERENCE_FILE
  - Identify and extract all sections labeled as "Pending Tasks", "TODO", "Refactors", or similar task-tracking sections
  - Parse each task and note any dependencies, priorities, or context provided
  - If no pending tasks are found, inform the user and ask if they want to work on a different section

- **Step 3: Analyze Tasks**
  - Review each pending task and assess:
    - Scope and complexity (simple, moderate, complex)
    - Dependencies on other tasks or files
    - Required changes (code, tests, documentation)
    - Potential risks or edge cases
  - Use Grep and Glob tools to locate relevant files mentioned in tasks
  - Read related code files to understand current implementation

- **Step 4: Create Implementation Plan**
  - Use TodoWrite tool to create a comprehensive task list with the following format:
    - Each pending task as a separate todo item
    - Break down complex tasks into smaller sub-tasks
    - Mark all as "pending" status initially
    - Use descriptive content and activeForm for each item
  - Order tasks logically (dependencies first, simpler before complex)
  - Estimate effort for each task (if apparent from the reference file)

- **Step 5: Ask Clarifying Questions**
  - Review the plan and identify any ambiguities or uncertainties
  - If you are less than 95% confident about any task's requirements, use AskUserQuestion to clarify:
    - Implementation approach preferences
    - Priority or order adjustments
    - Specific technical decisions (library choices, design patterns)
    - Scope boundaries (what's in/out of scope)
  - Continue asking questions until you reach 95% confidence level

- **Step 6: Present Plan for Approval**
  - Display the complete implementation plan with:
    - List of all tasks from TodoWrite
    - Estimated changes per task (files affected, test changes needed)
    - Any assumptions you're making
    - Risk assessment for each task
  - Use AskUserQuestion with a single yes/no question: "Do you approve this plan and want me to proceed with implementation?"

- **Step 7: Implement After Approval**
  - Only proceed if user explicitly approves the plan
  - Work through tasks sequentially using TodoWrite to track progress:
    - Mark current task as "in_progress" before starting
    - Use Edit or Write tools to implement changes
    - Follow project coding conventions and patterns (refer to CLAUDE.md if available)
    - Mark task as "completed" immediately after finishing each one
  - After completing each task or logical grouping:
    - Use Bash tool to run relevant tests (e.g., `just test`, `pytest`, etc.)
    - If tests fail, debug and fix issues before moving to next task
    - Keep user informed of progress with brief status updates

- **Step 8: Update Tests and Documentation**
  - After all tasks are implemented:
    - Use Grep to find test files related to changed code
    - Update or add tests as needed to maintain coverage
    - Run full test suite with `just test` or equivalent
    - Update CLAUDE.md, README.md, or other documentation if changes warrant it
    - Use Edit tool to mark completed tasks in REFERENCE_FILE as done (add ✅ or strikethrough)

- **Step 9: Final Verification**
  - Run complete test suite one final time
  - Use Bash to check for any linting errors (`just lint` if available)
  - Verify all TodoWrite items are marked "completed"
  - Ensure no uncommitted changes to critical files without user awareness

## Workflow

1. Validate that REFERENCE_FILE argument is provided; prompt user if missing
2. Read the reference file and locate the "Pending Tasks" section
3. Parse all pending tasks and analyze their scope, dependencies, and requirements
4. Use Grep/Glob to discover related code files and understand current state
5. Create a TodoWrite list with all tasks broken down into actionable items
6. Ask clarifying questions using AskUserQuestion until 95% confident
7. Present the complete plan and request explicit approval via AskUserQuestion
8. If approved, implement each task sequentially, updating TodoWrite status
9. Run tests after each task or logical grouping using Bash tool
10. Update related tests and documentation files
11. Mark tasks as completed in the original REFERENCE_FILE
12. Run final test suite and linting checks
13. Provide comprehensive summary report to user

## Report

After completing all tasks, provide a comprehensive summary report structured as follows:

### Tasks Completed
- List each task from REFERENCE_FILE with ✅ completion indicator
- Note the files changed for each task
- Mention any deviations from original task description (with justification)

### Testing Results
- Total tests run and pass/fail status
- Any new tests added (count and purpose)
- Linting check results (pass/fail)

### Documentation Updates
- List of documentation files updated (CLAUDE.md, README.md, etc.)
- Summary of documentation changes made
- Note if REFERENCE_FILE was updated to mark tasks complete

### Code Changes Summary
- Total files modified (count)
- Total lines added/removed (if git available)
- Key architectural or design decisions made
- Any technical debt introduced or resolved

### Outstanding Items
- Any tasks that couldn't be completed (with reasons)
- Follow-up tasks or recommendations for future work
- Known issues or limitations of implemented changes

### Recommendations
- Suggest next steps or related tasks from REFERENCE_FILE
- Highlight any potential improvements discovered during implementation
- Note any security, performance, or maintainability considerations

The report should be clear, actionable, and provide the user with complete visibility into what was accomplished and what remains to be done.
