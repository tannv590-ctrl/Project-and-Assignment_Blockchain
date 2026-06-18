from flask import Flask, render_template, request, jsonify, session
import hashlib
import json
import time
import base64

app = Flask(__name__)
app.secret_key = "blockchain_emr_secret_2024"

# =====================================================================
# CORE LOGIC (adapted from main.py)
# =====================================================================
class HospitalAndIPFSSimulation:
    def __init__(self):
        self.ipfs_storage = {}

    def generate_patient_secret_key(self):
        return "SECRET_KEY_AES_256_SIMULATED_PRO"

    def generate_patient_did(self, national_id):
        hashed_id = hashlib.sha256(national_id.encode('utf-8')).hexdigest()
        return f"did:emr:{hashed_id[:24]}"

    def create_raw_medical_record(self, patient_did, treatment_codes, total_amount):
        return {
            "patient_did": patient_did,
            "timestamp": int(time.time()),
            "treatment_codes": treatment_codes,
            "total_amount": total_amount
        }

    def compute_data_hash(self, emr_data):
        serialized_data = json.dumps(emr_data, sort_keys=True).encode('utf-8')
        return hashlib.sha256(serialized_data).hexdigest()

    def encrypt_and_upload_to_ipfs(self, emr_data, secret_key):
        serialized_str = json.dumps(emr_data, sort_keys=True)
        encoded_bytes = base64.b64encode(serialized_str.encode('utf-8'))
        ipfs_hash = "Qm" + hashlib.sha256(encoded_bytes).hexdigest()[:44]
        self.ipfs_storage[ipfs_hash] = encoded_bytes.decode()
        return ipfs_hash


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

    def get_all_entities(self):
        return self.entities


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

    def get_policy_info(self, policy_id):
        if policy_id in self.policy_templates:
            return {
                **self.policy_templates[policy_id],
                "approved_codes": list(self.approved_medications.get(policy_id, set()))
            }
        return None


class ClaimProcessingContract:
    def __init__(self, identity_contract, policy_contract):
        self.identity_contract = identity_contract
        self.policy_contract = policy_contract
        self.claims = {}
        self.claim_counter = 0

    def submit_and_process_claim(self, hospital_wallet, patient_did, ipfs_hash, data_hash, treatment_codes, total_amount):
        role = self.identity_contract.check_role(hospital_wallet)
        if role != "Hospital":
            return None, "TRANSACTION FAILED: Caller address is not a verified Hospital!", None

        policy_id = self.policy_contract.patient_policies.get(patient_did)
        if not policy_id:
            return None, "TRANSACTION FAILED: Patient does not have an active insurance policy!", None

        self.claim_counter += 1
        current_claim_id = self.claim_counter

        valid_codes, co_share_ratio, max_limit = self.policy_contract.verify_coverage(policy_id, treatment_codes)

        if len(valid_codes) == 0:
            approved_amount = 0
            status = "Rejected"
        else:
            calculated_amount = int(total_amount * (1.0 - co_share_ratio))
            approved_amount = min(calculated_amount, max_limit)
            status = "Approved"

        patient_copay = total_amount - approved_amount

        claim_record = {
            "claim_id": current_claim_id,
            "patient_did": patient_did,
            "ipfs_hash": ipfs_hash,
            "data_hash": data_hash,
            "status": status,
            "approved_amount": approved_amount,
            "patient_copay": patient_copay,
            "valid_codes": valid_codes,
            "total_amount": total_amount,
            "co_share_ratio": co_share_ratio,
            "max_limit": max_limit
        }
        self.claims[current_claim_id] = claim_record

        return current_claim_id, "TRANSACTION SUCCESSFUL", claim_record


# =====================================================================
# GLOBAL STATE (in-memory for session simulation)
# =====================================================================
ADMIN_WALLET = "SystemAdminCentralAddress"
HOSPITAL_WALLET = "QuangNamHospitalWalletAddress"
ATTACKER_WALLET = "MaliciousFakeAttackerWalletAddress"

offchain = HospitalAndIPFSSimulation()
identity_sc = IdentityContract(ADMIN_WALLET)
policy_sc = PolicyContract()
claim_sc = ClaimProcessingContract(identity_sc, policy_sc)

# Pre-register hospital and default policy so the UI works out-of-the-box
identity_sc.register_entity(ADMIN_WALLET, HOSPITAL_WALLET, "did:emr:hospital_quangnam", "Hospital")
policy_sc.create_policy_template(
    policy_id=999,
    max_limit=50000000,
    co_share_ratio=0.2,
    approved_codes=["ICD10-K29", "MED-AMOXICILLIN"]
)


# =====================================================================
# ROUTES
# =====================================================================
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/system-info", methods=["GET"])
def system_info():
    return jsonify({
        "admin_wallet": ADMIN_WALLET,
        "hospital_wallet": HOSPITAL_WALLET,
        "attacker_wallet": ATTACKER_WALLET,
        "entities": {k: v for k, v in identity_sc.entities.items()},
        "policies": {
            str(pid): {
                "max_limit": info["max_limit"],
                "co_share_ratio": info["co_share_ratio"],
                "approved_codes": list(policy_sc.approved_medications.get(pid, set()))
            }
            for pid, info in policy_sc.policy_templates.items()
        },
        "total_claims": claim_sc.claim_counter
    })


@app.route("/api/register-entity", methods=["POST"])
def register_entity():
    data = request.json
    caller = data.get("caller", ADMIN_WALLET)
    entity_address = data.get("entity_address", "")
    did = data.get("did", "")
    role = data.get("role", "Hospital")

    if not entity_address or not did:
        return jsonify({"success": False, "message": "Missing entity_address or did"}), 400

    success, msg = identity_sc.register_entity(caller, entity_address, did, role)
    return jsonify({
        "success": success,
        "message": msg,
        "entity": identity_sc.entities.get(entity_address)
    })


@app.route("/api/create-policy", methods=["POST"])
def create_policy():
    data = request.json
    policy_id = data.get("policy_id")
    max_limit = data.get("max_limit")
    co_share_ratio = data.get("co_share_ratio")
    approved_codes = data.get("approved_codes", [])

    if policy_id is None or max_limit is None or co_share_ratio is None:
        return jsonify({"success": False, "message": "Missing required fields"}), 400

    try:
        policy_id = int(policy_id)
        max_limit = int(max_limit)
        co_share_ratio = float(co_share_ratio)
    except ValueError:
        return jsonify({"success": False, "message": "Invalid numeric values"}), 400

    policy_sc.create_policy_template(policy_id, max_limit, co_share_ratio, approved_codes)
    return jsonify({
        "success": True,
        "message": f"Policy #{policy_id} created successfully",
        "policy": {
            "policy_id": policy_id,
            "max_limit": max_limit,
            "co_share_ratio": co_share_ratio,
            "approved_codes": approved_codes
        }
    })


@app.route("/api/register-patient", methods=["POST"])
def register_patient():
    data = request.json
    national_id = data.get("national_id", "")
    policy_id = data.get("policy_id")

    if not national_id:
        return jsonify({"success": False, "message": "Missing national_id"}), 400

    patient_did = offchain.generate_patient_did(national_id)

    if policy_id is not None:
        try:
            policy_id = int(policy_id)
            if policy_id not in policy_sc.policy_templates:
                return jsonify({"success": False, "message": f"Policy #{policy_id} does not exist"}), 400
            policy_sc.link_patient_to_policy(patient_did, policy_id)
        except ValueError:
            return jsonify({"success": False, "message": "Invalid policy_id"}), 400

    return jsonify({
        "success": True,
        "patient_did": patient_did,
        "national_id_hashed": hashlib.sha256(national_id.encode()).hexdigest(),
        "linked_policy": policy_id,
        "message": f"Patient registered with DID: {patient_did}"
    })


@app.route("/api/create-emr", methods=["POST"])
def create_emr():
    data = request.json
    patient_did = data.get("patient_did", "")
    treatment_codes_raw = data.get("treatment_codes", "")
    total_amount = data.get("total_amount")

    if not patient_did or not treatment_codes_raw or total_amount is None:
        return jsonify({"success": False, "message": "Missing required fields"}), 400

    if isinstance(treatment_codes_raw, str):
        treatment_codes = [c.strip() for c in treatment_codes_raw.split(",") if c.strip()]
    else:
        treatment_codes = treatment_codes_raw

    try:
        total_amount = int(total_amount)
    except ValueError:
        return jsonify({"success": False, "message": "Invalid total_amount"}), 400

    patient_key = offchain.generate_patient_secret_key()
    raw_emr = offchain.create_raw_medical_record(patient_did, treatment_codes, total_amount)
    data_hash = offchain.compute_data_hash(raw_emr)
    ipfs_hash = offchain.encrypt_and_upload_to_ipfs(raw_emr, patient_key)

    return jsonify({
        "success": True,
        "raw_emr": raw_emr,
        "data_hash": data_hash,
        "ipfs_hash": ipfs_hash,
        "encrypted_preview": offchain.ipfs_storage.get(ipfs_hash, "")[:80] + "...",
        "message": "EMR created, encrypted and uploaded to IPFS"
    })


@app.route("/api/submit-claim", methods=["POST"])
def submit_claim():
    data = request.json
    hospital_wallet = data.get("hospital_wallet", HOSPITAL_WALLET)
    patient_did = data.get("patient_did", "")
    ipfs_hash = data.get("ipfs_hash", "")
    data_hash = data.get("data_hash", "")
    treatment_codes_raw = data.get("treatment_codes", "")
    total_amount = data.get("total_amount")

    if not all([patient_did, ipfs_hash, data_hash, treatment_codes_raw, total_amount is not None]):
        return jsonify({"success": False, "message": "Missing required fields"}), 400

    if isinstance(treatment_codes_raw, str):
        treatment_codes = [c.strip() for c in treatment_codes_raw.split(",") if c.strip()]
    else:
        treatment_codes = treatment_codes_raw

    try:
        total_amount = int(total_amount)
    except ValueError:
        return jsonify({"success": False, "message": "Invalid total_amount"}), 400

    claim_id, msg, claim_record = claim_sc.submit_and_process_claim(
        hospital_wallet, patient_did, ipfs_hash, data_hash, treatment_codes, total_amount
    )

    if claim_id is None:
        return jsonify({"success": False, "message": msg, "claim": None})

    return jsonify({
        "success": True,
        "message": msg,
        "claim": claim_record
    })


@app.route("/api/claims", methods=["GET"])
def get_claims():
    claims_list = list(claim_sc.claims.values())
    return jsonify({"claims": claims_list, "total": len(claims_list)})


@app.route("/api/run-full-demo", methods=["POST"])
def run_full_demo():
    """Runs the full simulation from main.py and returns structured logs"""
    logs = []
    results = {}

    # Step 1: Setup
    logs.append({"step": 1, "type": "header", "msg": "STEP 1: Initializing On-Chain Identity & Policy Configurations"})

    success, msg = identity_sc.register_entity(ADMIN_WALLET, HOSPITAL_WALLET, "did:emr:hospital_quangnam", "Hospital")
    logs.append({"step": 1, "type": "info", "msg": f"Registered 'Hospital' authority role for wallet: {HOSPITAL_WALLET}"})

    approved_list = ["ICD10-K29", "MED-AMOXICILLIN"]
    policy_sc.create_policy_template(policy_id=999, max_limit=50000000, co_share_ratio=0.2, approved_codes=approved_list)
    logs.append({"step": 1, "type": "info", "msg": "Configured Insurance Plan #999 (Max Limit: 50,000,000 VND | Co-share: 20%)"})

    national_id = "044093001234"
    patient_did = offchain.generate_patient_did(national_id)
    policy_sc.link_patient_to_policy(patient_did, 999)
    logs.append({"step": 1, "type": "info", "msg": f"Patient National ID → Anonymous DID: {patient_did}"})
    logs.append({"step": 1, "type": "success", "msg": "Patient DID linked to Insurance Plan #999"})
    results["patient_did"] = patient_did

    # Step 2: EMR
    logs.append({"step": 2, "type": "header", "msg": "STEP 2: Patient Discharge - Off-Chain Record Structuring & Encryption"})
    patient_key = offchain.generate_patient_secret_key()
    treatment_items = ["ICD10-K29", "MED-AMOXICILLIN", "SERV-ENDOSCOPY"]
    total_cost = 2450000

    raw_emr = offchain.create_raw_medical_record(patient_did, treatment_items, total_cost)
    logs.append({"step": 2, "type": "data", "msg": "HIS generated raw EMR (Plaintext JSON)", "data": raw_emr})

    original_hash = offchain.compute_data_hash(raw_emr)
    logs.append({"step": 2, "type": "info", "msg": f"Cryptographic data hash: {original_hash}"})

    ipfs_hash = offchain.encrypt_and_upload_to_ipfs(raw_emr, patient_key)
    logs.append({"step": 2, "type": "success", "msg": f"Encrypted & pinned to IPFS: {ipfs_hash}"})
    results["ipfs_hash"] = ipfs_hash
    results["data_hash"] = original_hash
    results["raw_emr"] = raw_emr

    # Step 3: Security test
    logs.append({"step": 3, "type": "header", "msg": "STEP 3: Security Testing - Simulating Malicious Identity Exploit"})
    logs.append({"step": 3, "type": "warning", "msg": f"Attacker wallet ({ATTACKER_WALLET}) attempting unauthorized claim submission..."})
    _, error_msg, _ = claim_sc.submit_and_process_claim(
        ATTACKER_WALLET, patient_did, ipfs_hash, original_hash, treatment_items, total_cost
    )
    logs.append({"step": 3, "type": "blocked", "msg": f"RBAC Guard Result: {error_msg}"})

    # Step 4: Authorized claim
    logs.append({"step": 4, "type": "header", "msg": "STEP 4: Authorized Workflow - Automated Smart Contract Execution"})
    logs.append({"step": 4, "type": "info", "msg": f"Authorized hospital wallet submitting claim to blockchain..."})
    claim_id, success_msg, claim_record = claim_sc.submit_and_process_claim(
        HOSPITAL_WALLET, patient_did, ipfs_hash, original_hash, treatment_items, total_cost
    )
    logs.append({"step": 4, "type": "success", "msg": f"Execution Status: {success_msg}"})
    results["claim"] = claim_record

    return jsonify({"logs": logs, "results": results})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
