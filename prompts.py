playwright_python_prompt= """
    I have performed browser automation to generate an AgentHistoryList, extracting all actions performed by the agent.
    I want to accurately transform it into a Playwright script with BDD (Behavior-Driven Development) steps. The script should include all possible successful methods, interactions, and selectors, translated into human-readable steps.
                                             
    You are an expert in writing Python Playwright automation scripts using BDD principles (Given-When-Then) and the `pytest-bdd` library.
    Your task is to generate an **accurate and robust** Playwright script with corresponding BDD steps based on `AgentHistoryList`.
    **Do not include any suggestions in the Playwright script or BDD steps.**
 
    ### **Ensure the script and BDD steps follow these key principles:**
    1) Accurate Selectors:
    - Use stable and unique selectors (data-testid, aria-label, id).
    - Avoid fragile XPath-based selectors unless necessary.
    - **Handle multiple matching elements** by using `locator().first`, `locator().nth(0)`, or filtering based on text content (`locator().filter(has_text="Exact Text")`).
                                             
    2) Capturing All Possible successful methods:
    - Use Playwright's various interaction methods (click(), fill(), type(), etc.).
    - **Strictly avoid suggestions.**
    - Ensure form submissions, button clicks, popups, and navigation are covered.
    - If an element is inside an "<a>" tag or link, use `page.goto(href)` for direct navigation or `locator.click()` for interaction-based navigation.
                                             
    3) Handling Dynamic Elements:
    - Use `locator().first` or `locator().nth(0)` to resolve strict mode violations.
    - Use `get_by_text()` or `get_by_role()` with `exact=True` for precise selection.
 
    4) Error Handling & Resilience:
    - Ensure to use try-except blocks to handle unexpected failures.
 
    5) **Proper Handling of Async Methods:**
    - **Ensure that all asynchronous methods like `locator.inner_text()` are awaited** to avoid coroutine-related warnings.
    - Use `await locator.inner_text()` instead of directly referencing `locator.inner_text`.

    6) BDD Step Implementation:
    - Translate each action in the AgentHistoryList into a Given-When-Then BDD step.
    - Use `pytest-bdd` syntax for defining steps (e.g., `@given`, `@when`, `@then`).
    - Ensure each step has a clear and concise description.
    - Parameterize steps where appropriate to handle dynamic data.
                                             
    ### **Requirements:**
    - **Do NOT use `wait_for_selector`** in any part of the script.
    - Use **async functions** with Playwright.
    - Open **Chromium in headless mode**.
    - **Navigate** to the specified URL(s).
    - **Perform interactions** such as searching, clicking, extracting text, and handling form inputs.
    - **Implement error handling** (e.g., missing elements, timeouts, navigation failures).
    - **Ensure robustness** and reliability in the script.
    - **Close the browser** after execution.
    - Use `pytest-bdd` for BDD implementation.
 
    ### **Agent Interaction History:**
    {agent_hist}
 
    ### **Expected Output:**
    Generate a fully functional Playwright script in Python with Chromium launched in 'headless=False' mode, using correct selectors, methods, and error handling based on AgentHistoryList to ensure accurate automation. **Ensure that all Playwright async functions are properly awaited**. **Use appropriate attributes (`data-testid`, `aria-label`, `id`, `name`, `role`, etc.) to select elements effectively.**
    Also, generate corresponding BDD steps using `pytest-bdd` that accurately reflect the actions performed in the script. Return only the final script and BDD steps without explanations, comments, or additional formatting. Separate the Playwright script and BDD steps clearly.
    """

# playwright_python_prompt= """
#     I have performed browser automation to generate an AgentHistoryList, extracting all actions performed by the agent.
#     I want to accurately transform it into a Playwright script. The script should include all possible successful methods, interactions, and selectors.
                                             
#     You are an expert in writing Python Playwright automation scripts using Python.
#     Your task is to generate an **accurate and robust** Playwright script based on `AgentHistoryList`.
#     **Do not include any suggestions in the Playwright script.**
 
#     ### **Ensure the script follows these key principles:**
#     1) Accurate Selectors:
#     - Use stable and unique selectors (data-testid, aria-label, id).
#     - Avoid fragile XPath-based selectors unless necessary.
#     - **Handle multiple matching elements** by using `locator().first`, `locator().nth(0)`, or filtering based on text content (`locator().filter(has_text="Exact Text")`).
                                             
#     2) Capturing All Possible successful methods:
#     - Use Playwright's various interaction methods (click(), fill(), type(), etc.).
#     - **Strictly avoid suggestions.**
#     - Ensure form submissions, button clicks, popups, and navigation are covered.
#     - If an element is inside an "<a>" tag or link, use `page.goto(href)` for direct navigation or `locator.click()` for interaction-based navigation.
                                             
#     3) Handling Dynamic Elements:
#     - Use `locator().first` or `locator().nth(0)` to resolve strict mode violations.
#     - Use `get_by_text()` or `get_by_role()` with `exact=True` for precise selection.
 
#     4) Error Handling & Resilience:
#     - Ensure to use try-except blocks to handle unexpected failures.
 
#     5) **Proper Handling of Async Methods:**
#     - **Ensure that all asynchronous methods like `locator.inner_text()` are awaited** to avoid coroutine-related warnings.
#     - Use `await locator.inner_text()` instead of directly referencing `locator.inner_text`.
                                             
#     ### **Requirements:**
#     - **Do NOT use `wait_for_selector`** in any part of the script.
#     - Use **async functions** with Playwright.
#     - Open **Chromium in headless mode**.
#     - **Navigate** to the specified URL(s).
#     - **Perform interactions** such as searching, clicking, extracting text, and handling form inputs.
#     - **Implement error handling** (e.g., missing elements, timeouts, navigation failures).
#     - **Ensure robustness** and reliability in the script.
#     - **Close the browser** after execution.
 
#     ### **Agent Interaction History:**
#     {agent_hist}
 
#     ### **Expected Output:**
#     Generate a fully functional Playwright script in Python with Chromium launched in 'headless=False' mode, using correct selectors, methods, and error handling based on AgentHistoryList to ensure accurate automation. **Ensure that all Playwright async functions are properly awaited**.**Use appropriate attributes (`data-testid`, `aria-label`, `id`, `name`, `role`, etc.) to select elements effectively.** Return only the final script without explanations, comments, or additional formatting.
#     """

# playwright_python_prompt = """
# You are an expert Playwright automation developer. Your task is to convert the provided agent conversation history into a robust, production-ready Playwright script in Python.

# Analyze the entire conversation history containing "current_state", "action", and "interacted_elements" properties to understand the complete browser automation flow. Then generate a comprehensive Playwright script that precisely reproduces this interaction sequence.

# ## EXTRACTION RULES:
# 1. Extract exact URLs from "go_to_url" actions
# 2. Extract text inputs from "input_text" actions and their target elements
# 3. Extract click targets from "click_element" actions
# 4. Identify form submissions, navigation events, and verification points
# 5. Map "index" values in actions to the corresponding elements in "interacted_elements" array

# ## SELECTOR STRATEGY (STRICT PRIORITY ORDER - MUST FOLLOW):
# 1. USE CSS selectors (first priority) - Use concise, specific selectors
#  - EX: "html > body > app-root > app-portal > app-side-nav > mat-sidenav-container > mat-sidenav-content > app-my-profile > div > div:nth-of-type(3) > div > div:nth-of-type(2) > div:nth-of-type(2) > shared-input-field > div > input.form-control.inputField.ng-untouched.ng-pristine.ng-valid[placeholder=\"(xxx) xxx-xxxx\"][id=\"phoneNumber\"][type=\"text\"][autocomplete=\"dont-use-contactNo\"][required]
# 2. ID attributes (second priority) - Use page.locator('#elementId')
# 3. XPath (third priority) - Use only when ID and CSS aren't viable
# 4. Text content (last resort) - Use page.locator('text=Exact Text')
# 5. NEVER use data-test attributes unless explicitly mentioned in requirements

# ## CODE STRUCTURE:
# 1. Create a complete, standalone script with imports and proper async/await patterns
# 2. Organize into logical functions with appropriate error handling
# 3. Include proper setup/teardown with browser and context management
# 4. Use pytest fixtures if appropriate
# 5. Add type annotations for better code quality

# ## RELIABILITY REQUIREMENTS:
# 1. Add explicit waits before interactions with longer timeouts (minimum 30000ms)
# 2. Use page.wait_for_selector with state="attached" before trying state="visible"
# 3. Clear input fields before entering text using clear() method
# 4. Verify elements are visible and enabled before interaction
# 5. Add short delays (page.wait_for_timeout(1000)) after page loads and form submissions
# 6. For input fields that fail, try fallback selectors following the priority order

# ## ERROR HANDLING:
# 1. Implement try/except blocks for critical sections
# 2. Add screenshot capture on failures
# 3. Include proper cleanup in finally blocks
# 4. Log important steps and results
# 5. For elements that fail with one selector type, implement fallbacks in the strict priority order
# 6. When encountering selector timeouts, retry with the next selector type in the priority list

# ## SELECTOR FALLBACK MECHANISM:
# 1. Start with ID selector
# 2. If timeout occurs, try CSS selector
# 3. If still failing, try XPath
# 4. As last resort, try text-based selector
# 5. Document all attempted selectors in comments

# ## ASSERTIONS:
# 1. Add verification points after critical steps
# 2. Verify expected page state after navigation or significant actions


# Begin with a brief summary of the identified flow, then provide the complete, well-commented Playwright script that reproduces the exact sequence of actions from the conversation history. Ensure strict adherence to the selector priority order: ID > CSS > XPath > Text.

# Agent Interaction History:
# {agent_hist}

# Expected Output:
# Return a final, fully functional Playwright script in Python. The script should launch Chromium in 'headless=False' mode, applying correct selectors, methods, and error handling as specified by AgentHistoryList. All asynchronous calls must be properly awaited, and dynamic elements must be handled with precision using selected attributes such as data-testid, aria-label, id, name, and role. Provide only the final script without explanations, comments, or any additional formatting.

# The script should include code at the end to automatically run itself when executed, like this:
# ```python
# if __name__ == "__main__":
#     import asyncio
#     asyncio.run(main())
# """

# playwright_python_prompt = """
# I have conducted browser automation to create an AgentHistoryList that captures every action performed by the agent. I need to convert this list into a robust Playwright script in Python that precisely replicates these actions.

# You are an expert in crafting Python Playwright automation scripts. Your goal is to produce an accurate and resilient script based solely on the provided AgentHistoryList. The script should incorporate every viable method for interaction (click(), fill(), type(), etc.), and use selectors that reliably identify elements.

# Key guidelines for the script include:

# 1) Accurate Selectors:
#    - Rely on stable identifiers such as data-testid, aria-label, id, name, or role.
#    - Steer clear of brittle XPath selectors unless absolutely required.
#    - For elements with duplicate properties, use approaches like locator().first, locator().nth(0), or locator().filter(has_text="Exact Text").

# 2) Comprehensive Use of Successful Methods:
#    - Utilize Playwright's various action methods (like click(), fill(), type(), etc.) to cover all interactions.
#    - Avoid offering any suggestions within the script.
#    - Ensure that interactions including form submissions, button presses, popups, and navigation are all addressed.
#    - When dealing with anchor links, use page.goto(href) for direct navigation or locator.click() when appropriate.

# 3) Handling Dynamic Elements and Locators:
#    - When elements are dynamically loaded or their positions vary, use locator().first, locator().nth(0), get_by_text(), or get_by_role() with exact=True.
#    - Introduce strategies to identify dynamic locators using text or role-based filtering coupled with clear attribute identification (e.g., data-testid, aria-label).

# 4) Error Handling and Resilience:
#    - Integrate try-except blocks to gracefully handle unexpected failures and missing element scenarios.

# 5) Proper Async Handling:
#    - Ensure that every asynchronous method (e.g., await locator.inner_text()) is properly awaited to avoid coroutine warnings.

# Requirements:
#    - DO NOT use wait_for_selector anywhere in the script.
#    - Employ async functions for all Playwright-related tasks.
#    - Launch Chromium in headless mode when needed.
#    - Move to the specified URL(s) and execute interactions (searching, clicking, text extraction, form handling).
#    - Implement comprehensive error checking for elements, timeouts, and navigation issues.
#    - Guarantee that the script is robust and reliable.
#    - Make sure the browser is closed after execution.

# Agent Interaction History:
# {agent_hist}

# Expected Output:
# Return a final, fully functional Playwright script in Python. The script should launch Chromium in 'headless=False' mode, applying correct selectors, methods, and error handling as specified by AgentHistoryList. All asynchronous calls must be properly awaited, and dynamic elements must be handled with precision using selected attributes such as data-testid, aria-label, id, name, and role. Provide only the final script without explanations, comments, or any additional formatting.
# """

# 10. For validation of page load or any actions which involve loading time, add a step to wait for n number of seconds.
#     - Example: `Then I wait "10"`, `Then I wait "10"` etc...

EXECUTION_AGENT_FINAL_OUTPUT ="""

Review the provided agent interaction history, which includes various steps and elements (such as xpaths and buttons) the agent interacted with to complete a task. Focus on the final successful action of each sub-task.
User would have interacted with the browser to help acheive the task execution, and user may have added Interacted elements, convert and include them into appropriate detailed steps, BDD steps and Revised test case as well.

 Generate the following:
    1. Detailed steps for the task each step should be separated by newline character and also the step no i.e. '\n' ,
       - User would have interacted with the browser to help acheive the task execution, and user may have added Interacted elements, conver them into natural language detailed steps as well. 
       
       - Do not use any interacted elements data. rather convert them into natural language detailed steps as well.
       
       
        Example format: 
        "Step 1: Go to the URL "https://example.com"" \n,
         "Step 2: Click on the button "Login"",

    2. Generate BDD with these instructions -
        You are a expert in writing BDD steps using Gherkin syntax. Your task is to create BDD steps for the given test case.
        
            1. only one step definition at one step and never add two step at one time.
            2. Give BDD steps only for steps mentioned in the test case. Do not include any intermediate steps taken by you in case of failure in BDD. If failed steps are not accounted or mentioned in original test case do not include it.
            3. Important note: Each step should be separated by new line. Always give \n after every step.
            4. Refer `id` key from `interacted_elements` given in history to identify the locator and add # in front of id while generating BDD steps.
               - Example: If id is `username` then use `#username` in BDD steps.
            5.  If `id` is not present then use `xpath` as selector and  while generating BDD steps generate as mentioned below in example.
               - Example: If xpath is `html/body/div[2]/div[1]/div[2]/form/input[1]` then use `//html//body//div[2]//div[1]//div[2]//form//input[1]` in BDD steps.
            7. If tagname is 'select' with option then use steps similar to mention below example: 
               - Example:  When I select option "#edit-submitted-shipping-address-country" with value "India"
            8. For check option use only xpath instead of text   
            9. For Validation use text of the element. for example: When I see "Home".
            10. From the `interacted_elements` key, if there is `iframe` as part of `entire_parent_branch_path` then switch to that iframe using `When I switch to "iframe"`.
            11. For example In history where there is action of clicking "Show all applications" button then generate BDD step as
               - Example: `When I click "Applications menu"`.
        
            
            Strictly use only among these definitions while creating the BDD steps:
            'Given I open the url "{url}"',
                            'When I fill field for "{inputbox}" with value "{string}"',
                            'When I click "{Locator}"',
                            'Then I logout',
                            'Then I see "{string}"',
                            'When I select option "{string}" with value "{string}"',
                            'When I accept popup',
                            'When I append field for "{locator}" with value "{value}"',
                            'When I attach file with locator "{locator}" located in "{value}"',
                            'When I cancel popup',
                            'When I check option "{optionvalue}"',
                            'When I clear cookie',
                            'When I clear field "{locator}"',
                            'When I click "{locator}"',
                            'When I close current tab',
                            'When I close other tabs',
                            'Then I dont see text "{textvalue}"',
                            'Then I dont see text "{textvalue}" in "{locatorvalue}"',
                            'Then I dont check box "{locator}" is checked',
                            'Then I dont cookie "{value}"',
                            'Then I dont current url is "{url}"',
                            'Then I dont see element "{elementName}"',
                            'Then I dont see element "{elementName}" in dom',
                            'Then I dont see "{value}" in "{field}"',
                            'Then I dont see "{value}" in source',
                            'Then I dont see "{value}" in title',
                            'When I double click "{locator}"',
                            'When I drag from "{sourceelement}" to "{destinationelement}"',
                            'When I drag slider "{locator}" to "{offsetX}"',
                            'When I fill field for "{locator}" with value "{value}"',
                            'When I focus on "{locator}"',
                            'When I force click "{locator}"',
                            'When I force right click "{locator}"',
                            'Then I get attribute of "{locator}" and store it in "{varName}"',
                            'Then I get  all attribute of "{locator}" and store it in "{varName}"',
                            'Then I get css property of "{locator}" and store it in "{varName}"',
                            'Then I get all css property of "{locator}" and store it in "{varName}"',
                            'Then I get current url and store it in  "{varName}"',
                            'Then I get values of "{locator}" and store it in "{varName}"',
                            'Then I get all values of "{locator}" and store it in "{varName}"',
                            'When I open new tab',
                            'When I press key "{keyName}"',
                            'When I press down key "{keyName}"',
                            'When I press up key "{keyName}"',
                            'When I refresh the page',
                            'When I resize window',
                            'When I right click "{locator}"',
                            'When I scroll page to the bottom',
                            'When I scroll page to the top',
                            'When I scroll to "{locator}"',
                            'Then I see "{value}"',
                            'Then I see check box "{locator}" is checked',
                            'Then I see cookie "{cookieName}"',
                            'Then I see current url is "{url}"',
                            'Then I see element "{elementName}"',
                            'Then I see element "{elementName}" in dom',
                            'Then I see  "{urlFragment}" in current url',
                            'Then I see "{value}" in "{fieldlocator}"',
                            'Then I see "{text}" in popup',
                            'Then I see "{text}" in source',
                            'Then I see "{text}" in title',
                            'Then I see "{locatortext}" "{number}" times',
                            'Then I see title is "{titleName}"',
                            'When I select option "{select}" with value "{option}"',
                            'When I switch to main page',
                            'When I switch to "{page_number}"',
                            'When I switch to next tab',
                            'When I switch to next tab by "{number}"',
                            'When I switch previous tab',
                            'When I switch previous tab by "{number}"',
                            'When I switch to window "{window_name}"',
                            'When I uncheck option "{locator}"',
                            'Then I wait "{seconds}"',
                            'Then I generate name "{variable_name}" with value "{RandomNumDigit}"',
                            'Then I check value of "{variable1}" is "{variable2}"',
                            'Then I check for the duplicate value in "arrayName"',
                            'When I fill field for "{inputbox}" at position {number} with value {value}',
                            'When I fill field for textarea "{textarea}" at position {mumber} with value {value}',
                            'When I click on input for "{input}" at position {number}',
                            'When I click on list for "{listvalue}" at position {number}',
                            'When I click on input for "{inputPlaceholderName}"',
                            'When I pick "{option}" from option "{selectOptions}"',
                            'When I pick option "{optionText}" from "{selectOptionLocator}"',
                            'When I click on "{locator}"',
                            'When I select option "{option}" from "{selectLocator}" at position {number}',
                            'When I select option "{option}" from (placeholder|name|aria-label) "{locator}" at position {number}',
                            'When I select "{dropdownField}" from "{dropdownLocator}" dropdown',
                            'When I remove filtered value "{value}"',
                            'When I select (future|current) date at position {number}',
                            'When I select (button|text) "{locator}" at position {number}',
                            'When I get request id from "{dataVar}" and store in "{newVar}"',
            
        
                            Give output in this format only:
                            ### Scenario: Scenario of the Test case here\n
                                    Given I open the url "<url here>"
                                    When I fill field for "username" with value "username@email.com"
                                    When I fill field for "password" with value "givenPassword"
                                    Then I click "Login"
                                    Then I see "Home"
                            
 
                            
    3. A revised test case in JSON format(Initial test case would be more genric, we need a revised test case with all the relavant new steps taken to acheive this task execution), only replacing the 'testSteps' key with the new detailed steps while retaining other keys from the original test case.
       - IF there is no format in the test case then use the below format:
       "[{
        "testCaseId": "",
        "testDescription": "",
        "preconditions": "",
        "testSteps": [
            {
            "step": "",
            "expectedResults": ""
            },
            {
            "step": "",
            "expectedResults": ""
            },
            
        ],
        "expectedResults": "",
        "postconditions": ""
        }]"

    4. The test case ID from test case.
    - Extract the test case ID from the given input test case. The test case ID is a unique identifier for the test case and should be included in the output.
    - If there is no Test case ID in the input test case, return an name with some ID string for the test case ID.
    
    Provide the output strictly in the following format without any backticks or placeholders:
    {{
    "detailsSteps": "detailed steps to execute the test case",
    "bddSteps": "BDD steps to execute the test case",
    "revisedTestCase": ["revised test case in JSON format"],
    "testCaseId": ["test case Id extracted from given input test case"]
    }} 
"""
# When specifying locators, please use relative CSS selectors from `css_selectors` key instead of absolute ones. For example, the following is an absolute selector as it starts from the root:

#     html > body > div:nth-of-type(2) > div > div > div > form > input:nth-of-type(3).btn_action[type="submit"][id="login-button"].

#     In contrast, a relative selector would be:

#     input:nth-of-type(3).btn_action[type="submit"][id="login-button"].
    
#     Note: All locators for click etc must use  relative field from `css_selectors` key in history. only keep element from last value of `entire_parent_branch_path` in locator from `css_selectors` key.
    
