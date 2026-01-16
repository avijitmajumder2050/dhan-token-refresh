import os
import re
import time
import pyotp
import boto3
import requests
from playwright.sync_api import sync_playwright, TimeoutError

# =============================
# AWS CONFIG
# =============================
AWS_REGION = "ap-south-1"
ssm = boto3.client("ssm", region_name=AWS_REGION)

# =============================
# SSM HELPERS
# =============================
def get_param(name, decrypt=False):
    return ssm.get_parameter(
        Name=name,
        WithDecryption=decrypt
    )["Parameter"]["Value"]

def put_secure_param(name, value):
    ssm.put_parameter(
        Name=name,
        Value=value,
        Type="SecureString",
        Overwrite=True
    )

# =============================
# DHAN CONSENT URL
# =============================
def get_consent_url(client_id, api_key, api_secret):
    url = f"https://auth.dhan.co/app/generate-consent?client_id={client_id}"
    headers = {"app_id": api_key, "app_secret": api_secret}
    r = requests.post(url, headers=headers, timeout=15)
    r.raise_for_status()
    return (
        "https://auth.dhan.co/login/consentApp-login"
        f"?consentAppId={r.json()['consentAppId']}"
    )

# =============================
# MAIN
# =============================
def main():
    # ---- Load secrets ----
    client_id   = get_param("/dhan/client_id")
    api_key     = get_param("/dhan/api_key", True)
    api_secret  = get_param("/dhan/api_secret", True)
    totp_secret = get_param("/dhan/totp", True)
    mobile      = get_param("/dhan/mobile")
    pin         = get_param("/dhan/pin", True)

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )
        page = browser.new_page()

        print("➡ Opening consent URL")
        page.goto(get_consent_url(client_id, api_key, api_secret))

        # ---- Mobile ----
        page.fill("input", mobile)
        page.click("text=Proceed")

        # ---- TOTP ----
        page.wait_for_timeout(1500)
        page.fill("input", pyotp.TOTP(totp_secret).now())
        page.click("text=Proceed")

        # ---- PIN ----
        page.wait_for_timeout(1500)
        page.fill("input", pin)
        page.click("text=Proceed")

        # ---- WAIT FOR REDIRECT ----
        try:
            page.wait_for_url("**tokenId=**", timeout=30000)
        except TimeoutError:
            print("❌ Redirect failed")
            print("Current URL:", page.url)
            browser.close()
            raise

        print("✅ Redirected URL:", page.url)

        # ---- Extract token ----
        match = re.search(r"tokenId=([a-f0-9\-]+)", page.url)
        if not match:
            browser.close()
            raise RuntimeError(f"tokenId missing in URL: {page.url}")

        token_id = match.group(1)
        browser.close()

    # ---- Consume token ----
    token_url = (
        "https://auth.dhan.co/app/consumeApp-consent"
        f"?tokenId={token_id}"
    )
    r = requests.get(
        token_url,
        headers={"app_id": api_key, "app_secret": api_secret},
        timeout=15
    )
    r.raise_for_status()

    access_token = r.json()["accessToken"]

    # ---- Save token ----
    put_secure_param("/dhan/access_token", access_token)

    print("✅ DHAN access token updated successfully")

# =============================
if __name__ == "__main__":
    main()
