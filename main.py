import time
import logging
import pyotp
import boto3
from dhanhq import DhanLogin

# =============================
# LOGGING
# =============================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
# TOTP
# =============================
def generate_totp(totp_secret: str) -> str:
    return pyotp.TOTP(totp_secret).now()

# =============================
# DHAN TOKEN GENERATION (3 retries)
# =============================
def generate_access_token_with_retry(
    client_id: str,
    pin: str,
    totp_secret: str,
    retry_delay: int = 120,
    max_retries: int = 3
) -> str:

    dhan_login = DhanLogin(client_id)

    for attempt in range(1, max_retries + 1):
        logger.info("Generating Dhan access token (attempt %s/%s)", attempt, max_retries)

        
        token_data = dhan_login.generate_token(pin, generate_totp(totp_secret))

       

        if token_data and "accessToken" in token_data:
            logger.info("Token generated successfully.")
            return token_data["accessToken"]

        if attempt < max_retries:
            logger.info("Token response: %s", token_data)
            logger.warning(
                "accessToken not found, retrying in %s seconds...",
                retry_delay
            )
            time.sleep(retry_delay)

    raise RuntimeError(f"Failed to obtain accessToken after {max_retries} attempts")

# =============================
# MAIN
# =============================
def main():
    # ---- Load secrets from SSM ----
    client_id   = get_param("/dhan/client_id")
    pin         = get_param("/dhan/pin", True)
    totp_secret = get_param("/dhan/totp", True)

    # ---- Generate token ----
    access_token = generate_access_token_with_retry(
        client_id=client_id,
        pin=pin,
        totp_secret=totp_secret
    )

    logger.info("Access token generated successfully")

    # ---- Save token to SSM ----
    put_secure_param("/dhan/access_token", access_token)
    logger.info("Access token saved to SSM")

# =============================
if __name__ == "__main__":
    main()
