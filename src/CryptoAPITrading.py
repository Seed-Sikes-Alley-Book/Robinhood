import base64
import datetime
import json
from typing import Any, Dict, Optional
import uuid
import requests
from nacl.signing import SigningKey # type: ignore
import os 

from nacl.signing import SigningKey # type: ignore

# Generate a new signing key
signing_key = SigningKey.generate()

# Sign a message
signed = signing_key.sign(b"hello world")

# Verify
verify_key = signing_key.verify_key
verify_key.verify(signed)
