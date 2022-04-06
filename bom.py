#!/usr/bin/env python3
import logging
import os
import platform
import psutil
import random
import sys
import time
from selenium import webdriver
from time import monotonic

class BenchOMatic():
    """Automate browserbench.org testing across browsers using webdriver"""
    def __init__(self, options):
        self.driver = None
        self.detect_browsers()
        self.current_browser = None
        self.current_benchmark = None
        self.root_path = os.path.abspath(os.path.dirname(__file__))
        self.benchmarks = {
            'Speedometer 2.0': {
                'url': 'https://browserbench.org/Speedometer2.0/',
                'start': 'startTest();',
                'done': "return (document.getElementById('results-with-statistics') && document.getElementById('results-with-statistics').innerText.length > 0);",
                'result': "return parseInt(document.getElementById('result-number').innerText);",
                'confidence': "return parseFloat(document.getElementById('confidence-number').innerText.substring(2))"
            },
            'MotionMark 1.2': {
                'url': 'https://browserbench.org/MotionMark1.2/',
                'start': 'benchmarkController.startBenchmark();',
                'done': "return (document.querySelector('#results>.body>.score-container>.score').innerText.length > 0);",
                'result': "return parseFloat(document.querySelector('#results>.body>.score-container>.score').innerText);",
                'confidence': "document.querySelector('#results>.body>.score-container>.confidence').innerText.substring(1)"
            },
            'JetStream': {
                'url': 'https://browserbench.org/JetStream/',
                'start': 'JetStream.start();',
                'done': "return (document.querySelectorAll('#result-summary>.score').length > 0);",
                'result': "return parseFloat(document.querySelector('#result-summary>.score').innerText);"
            }
        }

    def run(self):
        """Run the requested tests"""
        benchmarks = self.benchmarks.keys()
        random.shuffle(benchmarks)
        for benchmark_name in benchmarks:
            self.current_benchmark = benchmark_name
            benchmark = self.benchmarks[benchmark_name]
            print('{}:'.format(benchmark_name))
            browsers = self.browsers.keys()
            random.shuffle(browsers)
            for name in browsers:
                browser = self.browsers[name]
                browser['name'] = name
                self.current_browser = name
                self.launch_browser(browser)
                self.current_benchmark = 'Speedometer'
                self.prepare_benchmark(benchmark)
                if self.run_benchmark(benchmark):
                    self.collect_result(benchmark)
                else:
                    logging.info('Benchmark failed')
                self.driver.close()
                try:
                    self.driver.quit()
                except Exception:
                    pass
    
    def launch_browser(self, browser):
        """Launch the selected browser"""
        logging.info('Launching {}...'.format(browser['name']))
        if browser['type'] == 'Chrome':
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.chrome.service import Service
            from webdriver_manager.chrome import ChromeDriverManager
            os.environ['WDM_LOG'] = '0'
            options = Options()
            options.binary_location = browser['exe']
            ver = 'latest'
            ver = browser['version'] if 'version' in browser else 'latest'
            self.driver = webdriver.Chrome(options=options, service=Service(ChromeDriverManager(version=ver).install()))
        elif browser['type'] == 'Safari':
            if 'driver' in browser:
                from selenium.webdriver.safari.options import Options
                options = Options()
                options.binary_location = browser['exe']
                options.use_technology_preview = True
                self.driver = webdriver.Safari(options=options)
            else:
                self.driver = webdriver.Safari()
        elif browser['type'] == 'Firefox':
            from selenium.webdriver.firefox.options import Options
            from selenium.webdriver.firefox.service import Service
            from webdriver_manager.firefox import GeckoDriverManager
            os.environ['WDM_LOG'] = '0'
            options = Options()
            options.binary_location = browser['exe']
            #ver = browser['version'] if 'version' in browser else 'latest'
            ver = 'latest'
            self.driver = webdriver.Firefox(options=options, service=Service(GeckoDriverManager(version=ver).install()))
        self.driver.set_page_load_timeout(600)
        self.driver.set_script_timeout(30)

        # Get the browser version
        if 'version' in self.driver.capabilities:
            self.current_browser += ' ' + self.driver.capabilities['version']
        elif 'browserVersion' in self.driver.capabilities:
            self.current_browser += ' ' + self.driver.capabilities['browserVersion']

        # Make sure all browsers use the same window size
        self.driver.set_window_position(0, 0)
        self.driver.set_window_size(1440, 900)

    def prepare_benchmark(self, benchmark):
        """Get ready to run the given benchmark"""
        self.driver.get(benchmark['url'])
        self.wait_for_idle()

    def run_benchmark(self, benchmark):
        """Run the benchmark and wait for it to finish"""
        logging.info('Starting benchmark...')
        self.driver.execute_script(benchmark['start'])

        # Wait up to an hour for the benchmark to run
        done = False
        end_time = monotonic() + 3600
        while not done and monotonic() < end_time:
            try:
                time.sleep(2)
                result = self.driver.execute_script(benchmark['done'])
                if result:
                    done = True
            except Exception:
                logging.exception('Error checking benchmark status')
        return done
    
    def collect_result(self, benchmark):
        """Collect the benchmark result"""
        result = 'N/A'
        try:
            result = self.driver.execute_script(benchmark['result'])
        except Exception:
            pass
        if 'confidence' in benchmark:
            confidence = 'N/A'
            try:
                confidence = self.driver.execute_script(benchmark['confidence'])
            except Exception:
                pass
            print('    {}: {} ± {}'.format(self.current_browser, result, confidence))
        else:
            print('    {}: {}'.format(self.current_browser, result))

        # Save the screnshot
        file_path = os.path.join(self.root_path, '{} - {}.png'.format(self.current_benchmark, self.current_browser))
        self.driver.get_screenshot_as_file(file_path)

    def wait_for_idle(self, timeout=30):
        """Wait for the system to go idle for at least 2 seconds"""
        logging.info("Waiting for Idle...")
        cpu_count = psutil.cpu_count()
        if cpu_count > 0:
            # No single core more than 30% or 10% total, whichever is higher
            target_pct = max(30. / float(cpu_count), 10.)
            idle_start = None
            end_time = monotonic() + timeout
            last_update = monotonic()
            idle = False
            while not idle and monotonic() < end_time:
                check_start = monotonic()
                pct = psutil.cpu_percent(interval=0.5)
                if pct <= target_pct:
                    if idle_start is None:
                        idle_start = check_start
                    if monotonic() - idle_start > 2:
                        idle = True
                else:
                    idle_start = None
                if not idle and monotonic() - last_update > 1:
                    last_update = monotonic()
                    logging.info("CPU Utilization: %0.1f%% (%d CPU's, %0.1f%% target)", pct, cpu_count, target_pct)

    def detect_browsers(self):
        """Find the various known-browsers in case they are not explicitly configured (ported from WebPageTest)"""
        browsers = {}
        plat = platform.system()
        if plat == "Windows":
            local_appdata = os.getenv('LOCALAPPDATA')
            program_files = str(os.getenv('ProgramFiles'))
            program_files_x86 = str(os.getenv('ProgramFiles(x86)'))
            # Allow 32-bit python to detect 64-bit browser installs
            if program_files == program_files_x86 and program_files.find(' (x86)') >= 0:
                program_files = program_files.replace(' (x86)', '')
            # Chrome
            paths = [program_files, program_files_x86, local_appdata]
            channels = ['Chrome', 'Chrome Beta']
            for channel in channels:
                for path in paths:
                    if path is not None and channel not in browsers:
                        chrome_path = os.path.join(path, 'Google', channel,
                                                'Application', 'chrome.exe')
                        if os.path.isfile(chrome_path):
                            browsers[channel] = {'exe': chrome_path, 'type': 'Chrome'}
            # Firefox browsers
            paths = [program_files, program_files_x86]
            for path in paths:
                if path is not None and 'Firefox' not in browsers:
                    firefox_path = os.path.join(path, 'Mozilla Firefox', 'firefox.exe')
                    if os.path.isfile(firefox_path):
                        browsers['Firefox'] = {'exe': firefox_path, 'type': 'Firefox'}
                if path is not None and 'Firefox' not in browsers:
                    firefox_path = os.path.join(path, 'Firefox', 'firefox.exe')
                    if os.path.isfile(firefox_path):
                        browsers['Firefox'] = {'exe': firefox_path, 'type': 'Firefox'}
                if path is not None and 'Firefox ESR' not in browsers:
                    firefox_path = os.path.join(path, 'Mozilla Firefox ESR', 'firefox.exe')
                    if os.path.isfile(firefox_path):
                        browsers['Firefox ESR'] = {'exe': firefox_path, 'type': 'Firefox'}
                if path is not None and 'Firefox Beta' not in browsers:
                    firefox_path = os.path.join(path, 'Mozilla Firefox Beta', 'firefox.exe')
                    if os.path.isfile(firefox_path):
                        browsers['Firefox Beta'] = {'exe': firefox_path, 'type': 'Firefox'}
                if path is not None and 'Firefox Beta' not in browsers:
                    firefox_path = os.path.join(path, 'Firefox Beta', 'firefox.exe')
                    if os.path.isfile(firefox_path):
                        browsers['Firefox Beta'] = {'exe': firefox_path, 'type': 'Firefox'}
            # Microsoft Edge (Chromium)
            paths = [program_files, program_files_x86, local_appdata]
            channels = ['Edge', 'Edge Dev']
            for channel in channels:
                for path in paths:
                    edge_path = os.path.join(path, 'Microsoft', channel, 'Application', 'msedge.exe')
                    if os.path.isfile(edge_path):
                        browser_name = 'Microsoft {0} (Chromium)'.format(channel)
                        if browser_name not in browsers:
                            browsers[browser_name] = {'exe': edge_path, 'type': 'Chrome'}
            if local_appdata is not None:
                edge_path = os.path.join(local_appdata, 'Microsoft', 'Edge SxS', 'Application', 'msedge.exe')
                if os.path.isfile(edge_path):
                    browsers['Microsoft Edge Canary (Chromium)'] = {'exe': edge_path, 'type': 'Chrome'}
            # Brave
            paths = [program_files, program_files_x86]
            for path in paths:
                if path is not None and 'Brave' not in browsers:
                    brave_path = os.path.join(path, 'BraveSoftware', 'Brave-Browser', 'Application', 'brave.exe')
                    if os.path.isfile(brave_path):
                        browsers['Brave'] = {'exe': brave_path, 'type': 'Chrome'}
        elif plat == "Linux":
            chrome_path = '/opt/google/chrome/chrome'
            if 'Chrome' not in browsers and os.path.isfile(chrome_path):
                browsers['Chrome'] = {'exe': chrome_path, 'type': 'Chrome'}
            beta_path = '/opt/google/chrome-beta/chrome'
            if 'Chrome Beta' not in browsers and os.path.isfile(beta_path):
                browsers['Chrome Beta'] = {'exe': beta_path, 'type': 'Chrome'}
            # Firefox browsers
            firefox_path = '/usr/lib/firefox/firefox'
            if 'Firefox' not in browsers and os.path.isfile(firefox_path):
                browsers['Firefox'] = {'exe': firefox_path, 'type': 'Firefox'}
            firefox_path = '/usr/bin/firefox'
            if 'Firefox' not in browsers and os.path.isfile(firefox_path):
                browsers['Firefox'] = {'exe': firefox_path, 'type': 'Firefox'}
            firefox_path = '/usr/lib/firefox-esr/firefox-esr'
            if 'Firefox ESR' not in browsers and os.path.isfile(firefox_path):
                browsers['Firefox ESR'] = {'exe': firefox_path, 'type': 'Firefox'}
            # Brave
            brave_path = '/opt/brave.com/brave/brave-browser'
            if 'Brave' not in browsers and os.path.isfile(brave_path):
                browsers['Brave'] = {'exe': brave_path, 'type': 'Chrome'}
            # Microsoft Edge
            edge_path = '/usr/bin/microsoft-edge-stable'
            if os.path.isfile(edge_path):
                if 'Microsoft Edge' not in browsers:
                    browsers['Microsoft Edge'] = {'exe': edge_path, 'type': 'Chrome'}
            edge_path = '/usr/bin/microsoft-edge-beta'
            if os.path.isfile(edge_path):
                if 'Microsoft Edge Beta' not in browsers:
                    browsers['Microsoft Edge Beta'] = {'exe': edge_path, 'type': 'Chrome'}
            edge_path = '/usr/bin/microsoft-edge-dev'
            if os.path.isfile(edge_path):
                if 'Microsoft Edge Dev' not in browsers:
                    browsers['Microsoft Edge Dev'] = {'exe': edge_path, 'type': 'Chrome'}

        elif plat == "Darwin":
            chrome_path = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
            if 'Chrome' not in browsers and os.path.isfile(chrome_path):
                browsers['Chrome'] = {'exe': chrome_path, 'type': 'Chrome'}
            chrome_path = '/Applications/Google Chrome Beta.app/Contents/MacOS/Google Chrome Beta'
            if 'Chrome Beta' not in browsers and os.path.isfile(chrome_path):
                browsers['Chrome Beta'] = {'exe': chrome_path, 'type': 'Chrome'}
            firefox_path = '/Applications/Firefox.app/Contents/MacOS/firefox'
            if 'Firefox' not in browsers and os.path.isfile(firefox_path):
                browsers['Firefox'] = {'exe': firefox_path, 'type': 'Firefox'}
            safari_path = '/Applications/Safari.app/Contents/MacOS/Safari'
            if 'Safari' not in browsers and os.path.isfile(safari_path):
                browsers['Safari'] = {'exe': safari_path, 'type': 'Safari'}
            """
            safari_path = '/Applications/Safari Technology Preview.app/Contents/MacOS/Safari Technology Preview'
            if 'Safari Technology Preview' not in browsers and os.path.isfile(safari_path):
                browsers['Safari Technology Preview'] = {'exe': safari_path, 'type': 'Safari',
                    'driver': '/Applications/Safari Technology Preview.app/Contents/MacOS/safaridriver'}
            """
            # Get the version of each
            import plistlib
            import re
            import requests
            for name in browsers:
                browser = browsers[name]
                plist_file = os.path.join(os.path.dirname(os.path.dirname(browser['exe'])), 'Info.plist')
                if os.path.isfile(plist_file):
                    with open(plist_file, 'rb') as f:
                        browser_version = plistlib.load(f)['CFBundleShortVersionString']
                        if name.startswith('Chrome'):
                            build = re.search(r'^([\d.][\d.][\d])', browser_version).group(1)
                            latest = requests.get('https://chromedriver.storage.googleapis.com/LATEST_RELEASE_{}'.format(build)).text
                            if latest:
                                browser['version'] = latest
                                # Get the version up to the build and fetch the latest matching Chromedriver build
                        else:
                            browser['version'] = browser_version

        logging.info('Detected Browsers:')
        for browser in browsers:
            logging.info('%s: %s', browser, browsers[browser]['exe'])
        self.browsers = browsers

if '__main__' == __name__:
    import argparse
    parser = argparse.ArgumentParser(description='Bench-o-matic', prog='bom')
    parser.add_argument('-v', '--verbose', action='count',
                        help="Increase verbosity (specify multiple times for more). -vvvv for full debug output.")
    options, _ = parser.parse_known_args()

    # Set up logging
    log_level = logging.CRITICAL
    if options.verbose is not None:
      if options.verbose == 1:
          log_level = logging.ERROR
      elif options.verbose == 2:
          log_level = logging.WARNING
      elif options.verbose == 3:
          log_level = logging.INFO
      elif options.verbose >= 4:
          log_level = logging.DEBUG
    logging.basicConfig(
        level=log_level, format="%(asctime)s.%(msecs)03d - %(message)s", datefmt="%H:%M:%S")

    # Kick off the actual benchmarking
    bom = BenchOMatic(options)
    bom.run()