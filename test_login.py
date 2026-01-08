import os
import json
import shutil
from datetime import datetime

def generate_universal_test_script():
    """Generate a universal test script that handles all modules dynamically"""
    
    script_content = '''import os
import sys
import json
import logging
import shutil
import importlib
from datetime import datetime
from playwright.sync_api import sync_playwright

# Add parent directory to path for imports
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

def setup_artifacts():
    if os.path.exists('artifacts'):
        shutil.rmtree('artifacts')
    os.makedirs('artifacts', exist_ok=True)

def setup_test_artifacts(test_id):
    test_folder = os.path.join('artifacts', test_id)
    screenshots_folder = os.path.join(test_folder, 'screenshots')
    videos_folder = os.path.join(test_folder, 'videos')
    os.makedirs(screenshots_folder, exist_ok=True)
    os.makedirs(videos_folder, exist_ok=True)
    return test_folder, screenshots_folder, videos_folder

def safe_screenshot(page, path):
    try:
        if not page.is_closed():
            # Disable font loading to prevent timeouts
            page.evaluate(\"document.fonts.clear(); document.body.style.fontFamily = 'Arial, sans-serif';\")
            page.evaluate(\"document.fonts.ready = Promise.resolve();\")
            page.wait_for_timeout(100)
            page.screenshot(path=path, animations='disabled')
            print(f\"Screenshot: {os.path.basename(path)}\")
            return
    except Exception as e:
        print(f\"Screenshot failed: {os.path.basename(path)} - {str(e)}\")


def load_all_testcases():
    """Load test cases from all JSON files in testcases folder"""
    testcases_dir = 'testcases'
    all_testcases = []
    
    if not os.path.exists(testcases_dir):
        print(f"Warning: {testcases_dir} folder not found")
        return []
    
    for filename in os.listdir(testcases_dir):
        if filename.endswith('.json'):
            filepath = os.path.join(testcases_dir, filename)
            try:
                with open(filepath, 'r') as f:
                    data = json.load(f)
                    if 'testCases' in data:
                        all_testcases.extend(data['testCases'])
                    print(f"Loaded {len(data.get('testCases', []))} test cases from {filename}")
            except Exception as e:
                print(f"Error loading {filename}: {e}")
    
    return all_testcases

def get_module_url(module_name):
    """Get URL for module from config/urls.py"""
    try:
        from config import urls
        url_map = {
            'login': getattr(urls, 'LOGIN_URL', 'https://dev.vox.snappod.ai/login'),
            'signup': getattr(urls, 'SIGNUP_URL', 'https://dev.vox.snappod.ai/signup'),
            'dashboard': getattr(urls, 'DASHBOARD_URL', 'https://dev.vox.snappod.ai/dashboard'),
        }
        return url_map.get(module_name.lower(), 'https://dev.vox.snappod.ai/login')
    except:
        return 'https://dev.vox.snappod.ai/login'

def get_module_locators(module_name):
    """Dynamically import locators for module"""
    try:
        module_path = f'config.{module_name.lower()}_locators'
        locators_module = importlib.import_module(module_path)
        return locators_module
    except:
        # Fallback to login locators
        class DefaultLocators:
            enter_your_email_input = "#login-email"
            enter_your_password_input = "#login-password"
            login_button = "button:has-text('Login')"
            forgot_password_a = "a:has-text('Forgot Password')"
        return DefaultLocators()

def validate_expected_outcomes(page, test_case):
    """Validate expected outcomes and return test result"""
    expected = test_case.get('expected', [])
    function_name = test_case.get('function', '').lower()
    inputs = test_case.get('inputs', {})
    
    validation_errors = []
    
    try:
        # Check for successful login/signup
        if 'successful' in function_name:
            if 'login' in function_name:
                if '/dashboard' not in page.url:
                    validation_errors.append(f"Expected redirect to dashboard, but URL is: {page.url}")
            elif 'signup' in function_name:
                if '/dashboard' not in page.url and 'success' not in page.url.lower():
                    validation_errors.append(f"Expected redirect to dashboard or success page, but URL is: {page.url}")
        
        # Check for validation errors on invalid inputs
        elif 'invalid' in function_name or 'empty' in function_name:
            expected_url = inputs.get('url', '')
            if expected_url and expected_url not in page.url:
                validation_errors.append(f"Expected to stay on {expected_url}, but URL is: {page.url}")
        
        # Check element visibility tests
        elif 'visibility' in function_name or 'elements' in function_name:
            steps = test_case.get('steps', [])
            for step in steps:
                if 'expect(' in step and 'toBeVisible()' in step:
                    if 'getByAltText' in step:
                        alt_text = step.split("getByAltText('")[1].split("')")[0]
                        try:
                            page.locator(f'img[alt="{alt_text}"]').wait_for(timeout=800)
                        except:
                            validation_errors.append(f"Element with alt text '{alt_text}' not visible")
                    elif 'getByRole' in step:
                        if 'heading' in step:
                            heading_text = step.split("name: '")[1].split("'")[0]
                            try:
                                page.locator(f'h1:has-text("{heading_text}"), h2:has-text("{heading_text}"), h3:has-text("{heading_text}")').wait_for(timeout=800)
                            except:
                                validation_errors.append(f"Heading '{heading_text}' not visible")
                        elif 'button' in step:
                            button_text = step.split("name: '")[1].split("'")[0]
                            try:
                                page.locator(f'button:has-text("{button_text}")').wait_for(timeout=1500)
                            except:
                                validation_errors.append(f"Button '{button_text}' not visible")
        
        # Check navigation tests
        elif 'navigate' in function_name:
            expected_url = inputs.get('expectedSignUpUrl') or inputs.get('expectedUrl')
            if expected_url and expected_url not in page.url:
                validation_errors.append(f"Expected navigation to {expected_url}, but URL is: {page.url}")
        
    except Exception as e:
        validation_errors.append(f"Validation error: {str(e)}")
    
    return validation_errors

def execute_test_steps(page, test_case, screenshots_folder, locators):
    """Execute test steps based on test case data"""
    inputs = test_case.get('inputs', {})
    module = test_case.get('module', 'login').lower()
    
    # Handle different input field names
    email_data = inputs.get('emailData') or inputs.get('validEmail') or inputs.get('email')
    password_data = inputs.get('passwordData') or inputs.get('validPassword') or inputs.get('password')
    
    step_counter = 1
    
    # Fill email if present
    if email_data:
        try:
            page.locator(locators.enter_your_email_input).fill(email_data)
            safe_screenshot(page, os.path.join(screenshots_folder, f'step_{step_counter:02d}_email_filled.png'))
            step_counter += 1
        except Exception as e:
            print(f"Email fill failed: {e}")
    
    # Fill password if present
    if password_data:
        try:
            page.locator(locators.enter_your_password_input).fill(password_data)
            safe_screenshot(page, os.path.join(screenshots_folder, f'step_{step_counter:02d}_password_filled.png'))
            step_counter += 1
        except Exception as e:
            print(f"Password fill failed: {e}")
    
    # Click main action button based on module
    try:
        if 'login' in module:
            page.locator(locators.login_button).click()
        elif 'signup' in module:
            page.locator(getattr(locators, 'signup_button', 'button:has-text("Sign Up")')).click()
        else:
            page.locator('button[type="submit"]').click()
        
        safe_screenshot(page, os.path.join(screenshots_folder, f'step_{step_counter:02d}_button_clicked.png'))
        step_counter += 1
        
        # Wait and capture result
        page.wait_for_timeout(800)
        safe_screenshot(page, os.path.join(screenshots_folder, f'step_{step_counter:02d}_result.png'))
        
    except Exception as e:
        print(f"Button click failed: {e}")
    
    # Handle special actions
    function_name = test_case.get('function', '').lower()
    
    if 'forgotpassword' in function_name:
        try:
            page.locator(locators.forgot_password_a).click()
            page.wait_for_timeout(500)
            safe_screenshot(page, os.path.join(screenshots_folder, f'step_{step_counter:02d}_forgot_password.png'))
        except Exception as e:
            print(f"Forgot password failed: {e}")
    
    elif 'google' in function_name:
        try:
            page.locator('button:has-text("Google")').click()
            page.wait_for_timeout(500)
            safe_screenshot(page, os.path.join(screenshots_folder, f'step_{step_counter:02d}_google_signin.png'))
        except Exception as e:
            print(f"Google signin failed: {e}")

def run_test(test_case):
    """Run individual test case"""
    test_id = test_case['id']
    module = test_case.get('module', 'Login Page').lower()
    
    # Extract module name from module field
    if 'login' in module:
        module_name = 'login'
    elif 'signup' in module:
        module_name = 'signup'
    else:
        module_name = 'login'  # default
    
    test_folder, screenshots_folder, videos_folder = setup_test_artifacts(test_id)
    
    # Setup logging
    log_file = os.path.join(test_folder, 'test.log')
    logging.basicConfig(filename=log_file, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(test_id)
    
    # Get module-specific URL and locators
    url = get_module_url(module_name)
    locators = get_module_locators(module_name)
    
    with sync_playwright() as p:
        headless_mode = globals().get('headless_mode', False)
        browser = p.chromium.launch(headless=headless_mode, args=['--disable-web-security', '--disable-features=VizDisplayCompositor', '--no-sandbox', '--disable-dev-shm-usage'])
        context = browser.new_context(
            record_video_dir=videos_folder,
            record_video_size={"width": 1280, "height": 720},
            ignore_https_errors=True,
            extra_http_headers={'Accept-Language': 'en-US,en;q=0.9'}
        )
        page = context.new_page()
        
        try:
            logger.info(f"Running test: {test_case['title']}")
            logger.info(f"Module: {module_name}, URL: {url}")
            
            # Navigate to page
            page.goto(url, timeout=5000)
            page.wait_for_load_state('domcontentloaded', timeout=1500)
            safe_screenshot(page, os.path.join(screenshots_folder, '00_initial.png'))
            
            # Execute test steps
            execute_test_steps(page, test_case, screenshots_folder, locators)
            
            # Validate expected outcomes
            validation_errors = validate_expected_outcomes(page, test_case)
            if validation_errors:
                raise Exception(f"Test validation failed: {'; '.join(validation_errors)}")
            
            # Final screenshot
            safe_screenshot(page, os.path.join(screenshots_folder, '99_final.png'))
            
            logger.info(f"Test {test_id} completed successfully")
            
        except Exception as e:
            logger.error(f"Test {test_id} failed: {str(e)}")
            safe_screenshot(page, os.path.join(screenshots_folder, 'error.png'))
            raise e
        finally:
            context.close()
            browser.close()

def generate_html_report(results):
    """Generate HTML report"""
    passed = sum(1 for r in results if r['status'] == 'PASSED')
    failed = sum(1 for r in results if r['status'] == 'FAILED')
    total = len(results)
    
    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Universal Test Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1 {{ color: #333; }}
        .summary {{ background: #f5f5f5; padding: 15px; border-radius: 5px; margin: 20px 0; }}
        .summary span {{ margin-right: 20px; font-weight: bold; }}
        .passed {{ color: green; }}
        .failed {{ color: red; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
        th {{ background-color: #4CAF50; color: white; }}
        tr:nth-child(even) {{ background-color: #f2f2f2; }}
        .status-passed {{ background-color: #d4edda; }}
        .status-failed {{ background-color: #f8d7da; }}
        a {{ color: #007bff; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
    </style>
</head>
<body>
    <h1>Universal Test Report</h1>
    <div class="summary">
        <span>Total: {total}</span>
        <span class="passed">Passed: {passed}</span>
        <span class="failed">Failed: {failed}</span>
        <span>Pass Rate: {(passed/total*100):.1f}%</span>
        <span>Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</span>
    </div>
    <table>
        <tr>
            <th>Test ID</th>
            <th>Module</th>
            <th>Title</th>
            <th>Status</th>
            <th>Artifacts</th>
        </tr>"""
    
    for result in results:
        status_class = 'status-passed' if result['status'] == 'PASSED' else 'status-failed'
        html += f"""        <tr class="{status_class}">
            <td>{result['id']}</td>
            <td>{result.get('module', 'N/A')}</td>
            <td>{result['title']}</td>
            <td>{result['status']}</td>
            <td><a href="{result['id']}/screenshots/" target="_blank">Screenshots</a> | 
                <a href="{result['id']}/videos/" target="_blank">Videos</a> | 
                <a href="{result['id']}/test.log" target="_blank">Log</a></td>
        </tr>"""
    
    html += """    </table>
</body>
</html>"""
    
    with open('artifacts/report.html', 'w') as f:
        f.write(html)

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Run universal test cases')
    parser.add_argument('--test', '-t', help='Run specific test case', default=None)
    parser.add_argument('--module', '-m', help='Run tests for specific module (login, signup, etc.)', default=None)
    parser.add_argument('--headless', help='Run in headless mode (no browser window)', action='store_true')
    args = parser.parse_args()
    
    # Set global headless mode
    globals()['headless_mode'] = args.headless
    
    print("🚀 Universal Test Runner Starting...")
    
    setup_artifacts()
    all_testcases = load_all_testcases()
    
    if not all_testcases:
        print("❌ No test cases found!")
        exit(1)
    
    print(f"📋 Found {len(all_testcases)} total test cases")
    
    # Filter test cases
    test_cases_to_run = all_testcases
    
    if args.test:
        test_cases_to_run = [tc for tc in all_testcases if tc['id'] == args.test]
        if not test_cases_to_run:
            print(f"❌ Test case {args.test} not found!")
            print(f"Available test cases: {', '.join([tc['id'] for tc in all_testcases])}")
            exit(1)
    
    if args.module:
        test_cases_to_run = [tc for tc in test_cases_to_run if args.module.lower() in tc.get('module', '').lower()]
        print(f"🔍 Filtered to {len(test_cases_to_run)} test cases for module: {args.module}")
    
    results = []
    
    for i, test_case in enumerate(test_cases_to_run, 1):
        print(f"\\n[{i}/{len(test_cases_to_run)}] Running {test_case['id']}: {test_case['title']}")
        try:
            run_test(test_case)
            results.append({
                'id': test_case['id'], 
                'title': test_case['title'], 
                'module': test_case.get('module', 'N/A'),
                'status': 'PASSED'
            })
            print("✅ PASSED")
        except Exception as e:
            results.append({
                'id': test_case['id'], 
                'title': test_case['title'], 
                'module': test_case.get('module', 'N/A'),
                'status': 'FAILED'
            })
            print(f"❌ FAILED: {str(e)}")
    
    # Generate report
    generate_html_report(results)
    
    # Summary
    passed = sum(1 for r in results if r['status'] == 'PASSED')
    failed = sum(1 for r in results if r['status'] == 'FAILED')
    
    print(f"\\n📊 Test Summary:")
    print(f"   Total: {len(results)}")
    print(f"   Passed: {passed}")
    print(f"   Failed: {failed}")
    print(f"   Pass Rate: {(passed/len(results)*100):.1f}%")
    print(f"\\n📄 HTML Report: artifacts/report.html")
'''
    
    return script_content

def main():
    print("Generating Universal Test Script...")
    
    # Generate the script content
    script_content = generate_universal_test_script()
    
    # Write to file
    output_file = "scripts/test_universal_autogenerated.py"
    
    # Backup existing file if it exists
    if os.path.exists(output_file):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = f"scripts/test_universal_autogenerated_backup_{timestamp}.py"
        shutil.copy2(output_file, backup_file)
        print(f"Backed up existing file to: {backup_file}")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(script_content)
    
    print(f"Universal test script generated: {output_file}")
    print("\nUsage:")
    print(f"   python {output_file}                    # Run all tests")
    print(f"   python {output_file} --test TC-LOGIN-001  # Run specific test")
    print(f"   python {output_file} --module login       # Run all login tests")
    print(f"   python {output_file} --module signup      # Run all signup tests")

if __name__ == "__main__":
    main()
