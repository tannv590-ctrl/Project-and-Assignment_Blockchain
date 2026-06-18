import hashlib
import json
import time
import base64

# =====================================================================
# PART 1: OFF-CHAIN SYSTEM SIMULATION (HOSPITAL HIS & IPFS)
# =====================================================================
class HospitalAndIPFSSimulation:
    def __init__(self):
        self.ipfs_storage = {}  # Simulated IPFS storage dictionary
        print("[OFF-CHAIN SYSTEM] Successfully initialized HIS and IPFS environment.")

    def generate_patient_secret_key(self):
        """Generates a simulated symmetric encryption key for the patient's record"""
        return "SECRET_KEY_AES_256_SIMULATED_PRO"

    def generate_patient_did(self, national_id):
        """Hashes National ID (CCCD) using SHA-256 to generate a decentralized identifier (DID)"""
        hashed_id = hashlib.sha256(national_id.encode('utf-8')).hexdigest()
        return f"did:emr:{hashed_id[:24]}"

    def create_raw_medical_record(self, patient_did, treatment_codes, total_amount):
        """Packages medical data into a standard JSON structure"""
        return {
            "patient_did": patient_did,
            "timestamp": int(time.time()),
            "treatment_codes": treatment_codes,
            "total_amount": total_amount
        }

    def compute_data_hash(self, emr_data):
        """Generates a cryptographic hash of the raw data to ensure data integrity"""
        serialized_data = json.dumps(emr_data, sort_keys=True).encode('utf-8')
        return hashlib.sha256(serialized_data).hexdigest()

    def encrypt_and_upload_to_ipfs(self, emr_data, secret_key):
        """Simulates EMR encryption via Base64 and uploads it to IPFS, returning an IPFS Hash (CID)"""
        serialized_str = json.dumps(emr_data, sort_keys=True)
        
        # Simulating symmetric encryption by converting the JSON string into a secure Base64 encoded byte string
        encoded_bytes = base64.b64encode(serialized_str.encode('utf-8'))
        
        # Simulating IPFS Content Identifier (CID) generation starting with the characteristic 'Qm' prefix
        ipfs_hash = "Qm" + hashlib.sha256(encoded_bytes).hexdigest()[:44]
        self.ipfs_storage[ipfs_hash] = encoded_bytes
        return ipfs_hash


# =====================================================================
# PART 2: ON-CHAIN SMART CONTRACT SIMULATION (BLOCKCHAIN STATE)
# =====================================================================
class IdentityContract:
    def __init__(self, admin_address):
        self.admin = admin_address
        self.entities = {admin_address: {"did": "did:emr:admin", "role": "Admin", "isActive": True}}

    def register_entity(self, caller, entity_address, did, role):
        if caller != self.admin:
            return False, "ERROR: Only System Admin has permission to register identity!"
        self.entities[entity_address] = {"did": did, "role": role, "isActive": True}
        return True, "SUCCESS"

    def check_role(self, entity_address):
        if entity_address in self.entities and self.entities[entity_address]["isActive"]:
            return self.entities[entity_address]["role"]
        return "None"


class PolicyContract:
    def __init__(self):
        self.policy_templates = {}
        self.approved_medications = {}
        self.patient_policies = {}

    def create_policy_template(self, policy_id, max_limit, co_share_ratio, approved_codes):
        self.policy_templates[policy_id] = {"max_limit": max_limit, "co_share_ratio": co_share_ratio}
        self.approved_medications[policy_id] = set(approved_codes)

    def link_patient_to_policy(self, patient_did, policy_id):
        self.patient_policies[patient_did] = policy_id

    def verify_coverage(self, policy_id, treatment_codes):
        if policy_id not in self.policy_templates:
            return [], 0.0, 0
        template = self.policy_templates[policy_id]
        approved_set = self.approved_medications[policy_id]
        valid_codes = [code for code in treatment_codes if code in approved_set]
        return valid_codes, template["co_share_ratio"], template["max_limit"]


class ClaimProcessingContract:
    def __init__(self, identity_contract, policy_contract):
        self.identity_contract = identity_contract
        self.policy_contract = policy_contract
        self.claims = {}
        self.claim_counter = 0

    def submit_and_process_claim(self, hospital_wallet, patient_did, ipfs_hash, data_hash, treatment_codes, total_amount):
        # 1. Access Control Verification via Identity Contract (RBAC)
        role = self.identity_contract.check_role(hospital_wallet)
        if role != "Hospital":
            return None, "TRANSACTION FAILED: Caller address is not a verified Hospital!"

        # 2. Insurance Validity Check via Policy Contract
        policy_id = self.policy_contract.patient_policies.get(patient_did)
        if not policy_id:
            return None, "TRANSACTION FAILED: Patient does not have an active insurance policy!"

        self.claim_counter += 1
        current_claim_id = self.claim_counter

        # 3. Automated Policy Matching & Cross-Contract Verification
        valid_codes, co_share_ratio, max_limit = self.policy_contract.verify_coverage(policy_id, treatment_codes)

        if len(valid_codes) == 0:
            approved_amount = 0
            status = "Rejected"
        else:
            # Automated calculation engine based on Co-share Ratio
            calculated_amount = int(total_amount * (1.0 - co_share_ratio))
            # Enforcement of coverage maximum threshold limits
            approved_amount = min(calculated_amount, max_limit)
            status = "Approved"

        patient_copay = total_amount - approved_amount

        # Commit state updates to the simulated Blockchain Ledger
        self.claims[current_claim_id] = {
            "claim_id": current_claim_id,
            "patient_did": patient_did,
            "ipfs_hash": ipfs_hash,
            "data_hash": data_hash,
            "status": status,
            "approved_amount": approved_amount,
            "patient_copay": patient_copay
        }

        # Emit Blockchain Event to signal external oracle/payment gateways
        print(f"\n[BLOCKCHAIN EVENT] >>> Emitted Event 'ClaimProcessed' (Claim ID: #{current_claim_id})")
        print(f"    - Settlement Status: {status}")
        print(f"    - Approved Insurer Amount: {approved_amount:,} VND")
        print(f"    - Patient Responsibility (Co-pay): {patient_copay:,} VND")
        print(f"    - Proof Anchor (IPFS Hash Pointer): {ipfs_hash}")
        print(f"    - Integrity Verification (Data Hash): {data_hash}")

        return current_claim_id, "TRANSACTION SUCCESSFUL"


# =====================================================================
# PART 3: END-TO-END SYSTEM INTEGRATION AND COORDINATION SCENARIO
# =====================================================================
def run_full_system_simulation():
    print("==========================================================================")
    print("      LAUNCHING DECENTRALIZED AUTOMATED CLAIM & EMR SIMULATION ENGINE     ")
    print("==========================================================================\n")
    
    # 1. Instantiate Off-chain Infrastructure
    offchain_infrastructure = HospitalAndIPFSSimulation()
    
    # Simulating Blockchain Wallet Addresses
    admin_wallet = "SystemAdminCentralAddress"
    hospital_wallet = "QuangNamHospitalWalletAddress"
    attacker_wallet = "MaliciousFakeAttackerWalletAddress"
    
    # Deploying Simulated Smart Contracts
    identity_sc = IdentityContract(admin_wallet)
    policy_sc = PolicyContract()
    claim_sc = ClaimProcessingContract(identity_sc, policy_sc)
    
    print("\n--- STEP 1: INITIALIZING ON-CHAIN IDENTITY & POLICY CONFIGURATIONS ---")
    # Granting proper authorization role to the hospital
    identity_sc.register_entity(admin_wallet, hospital_wallet, "did:emr:hospital_quangnam", "Hospital")
    print(f"[*] Registered 'Hospital' authority role for wallet: {hospital_wallet}")
    
    # Configure Policy Plan #999: Max limit 50M, Co-share 20% (Insurer covers 80% of approved codes)
    approved_treatment_list = ["ICD10-K29", "MED-AMOXICILLIN"]
    policy_sc.create_policy_template(policy_id=999, max_limit=50000000, co_share_ratio=0.2, approved_codes=approved_treatment_list)
    print("[*] Configured Insurance Plan #999 (Max Limit: 50,000,000 VND | Co-share Ratio: 20%)")
    
    # Patient admission, mapping PII to an anonymized Decentralized Identifier (DID)
    national_id_input = "044093001234"
    patient_did = offchain_infrastructure.generate_patient_did(national_id_input)
    policy_sc.link_patient_to_policy(patient_did, policy_id=999)
    print(f"[*] Patient Admitted. Converted National ID into Anonymous Patient DID: {patient_did}")
    print("[*] Linked Patient DID to Insurance Plan #999 on-chain state variables.")
    
    print("\n--- STEP 2: PATIENT DISCHARGE - OFF-CHAIN RECORD STRUCTURING & ENCRYPTION ---")
    patient_key = offchain_infrastructure.generate_patient_secret_key()
    treatment_items = ["ICD10-K29", "MED-AMOXICILLIN", "SERV-ENDOSCOPY"] # SERV-ENDOSCOPY is non-covered
    total_cost = 2450000 # 2,450,000 VND
    
    # Hospital Information System creates raw EMR
    raw_emr = offchain_infrastructure.create_raw_medical_record(patient_did, treatment_items, total_cost)
    print(f"[*] HIS generated raw medical record (Plaintext JSON):\n{json.dumps(raw_emr, indent=4)}")
    
    # Compute immutable original data hash
    original_hash = offchain_infrastructure.compute_data_hash(raw_emr)
    print(f"[*] Computed cryptographic integrity data hash: {original_hash}")
    
    # Encrypt and upload to distributed storage network (IPFS)
    ipfs_hash = offchain_infrastructure.encrypt_and_upload_to_ipfs(raw_emr, patient_key)
    print(f"[*] Encryption completed. Record pinned to IPFS. Returned IPFS Hash pointer: {ipfs_hash}")
    
    print("\n--- STEP 3: SECURITY TESTING - SIMULATING MALICIOUS IDENTITY EXPLOIT ---")
    print(f"[*] Unauthorized malicious wallet ({attacker_wallet}) executing submit_and_process_claim...")
    _, error_msg = claim_sc.submit_and_process_claim(
        hospital_wallet=attacker_wallet,
        patient_did=patient_did,
        ipfs_hash=ipfs_hash,
        data_hash=original_hash,
        treatment_codes=treatment_items,
        total_amount=total_cost
    )
    print(f"[SECURITY GUARD RESULT]: {error_msg}")
    
    print("\n--- STEP 4: AUTHORIZED WORKFLOW - AUTOMATED SMART CONTRACT EXECUTION ---")
    print(f"[*] Authorized Hospital wallet submitting metadata transaction parameters to blockchain...")
    
    # FORWARDING OFF-CHAIN PROCESSING OUTPUTS DIRECTLY INTO THE SMART CONTRACT ENGINE
    claim_id, success_msg = claim_sc.submit_and_process_claim(
        hospital_wallet=hospital_wallet,
        patient_did=patient_did,
        ipfs_hash=ipfs_hash,
        data_hash=original_hash,
        treatment_codes=treatment_items,
        total_amount=total_cost
    )
    
    print(f"\n[*] Execution Status: {success_msg}")
    print("==========================================================================\n")

if __name__ == "__main__":
    run_full_system_simulation()