from pathlib import Path
from nacl.signing import SigningKey
import base64

ROOT = Path(__file__).resolve().parent
PRIVATE = ROOT / 'ed25519_private.key'
PUBLIC = ROOT / 'ed25519_public.key'

def main():
    ROOT.mkdir(parents=True, exist_ok=True)
    sk = SigningKey.generate()
    seed = sk._seed  # 32 bytes
    vk = sk.verify_key
    PRIVATE.write_bytes(seed)
    PUBLIC.write_bytes(vk.encode())
    print('Private key (seed, 32 bytes) saved to:', PRIVATE)
    print('Public key saved to:', PUBLIC)
    print('Public key (base64):', base64.b64encode(vk.encode()).decode('ascii'))

if __name__ == '__main__':
    main()

