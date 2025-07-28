"""KYC Verifier for Computer Vision Service"""

class KYCVerifier:
    def __init__(self):
        pass
        
    def verify_document(self, image_data: bytes) -> dict:
        return {"verified": False, "confidence": 0.5} 