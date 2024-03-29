REFUEL = True
REFUEL_THRESHOLD = 0.2
API_KEY = ""
API_SECRET = ""
PASSPHRASE = ''
MIN_AMOUNT_WITHDRAW, MAX_AMOUNT_WITHDRAW = 0.2, 0.6

SHUFFLE_ACCOUNTS = True
MAX_THREAD = 2

AMOUNT_TO_STAKE_MIN, AMOUNT_TO_STAKE_MAX = 0.01, 0.05
SLEEP_FOR_THREAD_MIN, SLEEP_FOR_THREAD_MAX = 1, 2
SLEEP_MIN, SLEEP_MAX = 1, 2

GOOGLE_FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSdaNMHHDIki4XZgzES9DyCIds6jzfGtY28o5AONrlRmVUgIwg/viewform"
NODE = "https://fullnode.mainnet.aptoslabs.com/v1"

# If you`re going to use authentication by IP - you need to add you IP to whitelist on SmartProxy portal:
# Visit this link "https://dashboard.smartproxy.com/mobile-proxies/proxy-setup"
# Otherwise you should use link with credentials and paste it below, it looks something like this:
# f"http://{username}:{password}@gate.smartproxy.com:10001"

SMART_PROXY_URL = 'http://gate.smartproxy.com:7000'
TWO_CAPTCHA_KEY = ''
