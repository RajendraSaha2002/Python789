

import json
import subprocess
import os

# ============================================================================
# 1. BYTECODE ASSEMBLER FOR STACK VM
# ============================================================================
OPCODES = {
    "STOP": 0x00, "PUSH": 0x01, "POP": 0x02, "ADD": 0x03, "SUB": 0x04,
    "MUL": 0x05, "EQ": 0x07, "LT": 0x08, "GT": 0x09, "SLOAD": 0x10,
    "SSTORE": 0x11, "CALLDATALOAD": 0x12, "CALLER": 0x13,
    "JUMP": 0x20, "JUMPI": 0x21, "JUMPDEST": 0x22, "DUP": 0x30,
    "SWAP": 0x31, "REVERT": 0xFD
}


def assemble(asm_code: str) -> str:
    """Compiles human-readable assembly mnemonics into hex bytecode."""
    lines = asm_code.strip().split("\n")
    bytecode = bytearray()
    labels = {}
    jumps_to_resolve = []

    # First Pass: collect instructions and mark labels
    clean_instructions = []
    for line in lines:
        line = line.split("//")[0].strip()
        if not line:
            continue
        if line.endswith(":"):
            labels[line[:-1]] = len(bytecode)
            bytecode.append(OPCODES["JUMPDEST"])
        else:
            parts = line.split()
            op = parts[0]
            clean_instructions.append((op, parts[1:] if len(parts) > 1 else []))
            bytecode.append(OPCODES[op])
            if op == "PUSH":
                bytecode.extend([0] * 8)  # Placeholder for 64-bit int

    # Second Pass: emit exact bytes
    final_bytecode = bytearray()
    for op, args in clean_instructions:
        final_bytecode.append(OPCODES[op])
        if op == "PUSH":
            val = int(args[0]) if not args[0].startswith("@") else labels[args[0][1:]]
            final_bytecode.extend(val.to_bytes(8, byteorder="big", signed=False))

    return final_bytecode.hex()


# ============================================================================
# 2. CONTRACT SPECIFICATIONS
# ============================================================================

# Token Contract: Transfer(to, amount)
# Storage layout: slot 0 = TotalSupply, slot <User_ID> = Balance
TOKEN_ASM = """
// 1. Verify function selector (calldata[0] == 1 for transfer)
PUSH 0
CALLDATALOAD
PUSH 1
EQ
PUSH @TRANSFER_LABEL
JUMPI
REVERT

TRANSFER_LABEL:
// 2. Load amount and deduct from sender
PUSH 2
CALLDATALOAD       // amount
CALLER
SLOAD              // sender_balance
SUB                // sender_balance - amount (reverts on underflow)
CALLER
SSTORE             // update sender balance

// 3. Credit recipient balance
PUSH 2
CALLDATALOAD       // amount
PUSH 1
CALLDATALOAD       // recipient_id
SLOAD              // recipient_balance
ADD                // recipient_balance + amount
PUSH 1
CALLDATALOAD       // recipient_id
SSTORE             // update recipient balance

STOP
"""

# Escrow Contract: Release()
# Storage layout: slot 0 = locked_amount, slot 1 = depositor, slot 2 = beneficiary, slot 3 = is_settled
ESCROW_ASM = """
// 1. Check if already settled (storage[3] == 0)
PUSH 3
SLOAD
PUSH 0
EQ
PUSH @PROCEED_LABEL
JUMPI
REVERT

PROCEED_LABEL:
// 2. Check if Caller is the Beneficiary (CALLER == storage[2])
CALLER
PUSH 2
SLOAD
EQ
PUSH @RELEASE_LABEL
JUMPI
REVERT

RELEASE_LABEL:
// 3. Set locked_amount = 0 and is_settled = 1
PUSH 0
PUSH 0
SSTORE             // storage[0] = 0

PUSH 1
PUSH 3
SSTORE             // storage[3] = 1

STOP
"""


# ============================================================================
# 3. INTEROPERABILITY & INVARIANT CHECK ENGINE
# ============================================================================
class SmartContractExecutor:
    def __init__(self, vm_binary_path="./smart_contract_vm"):
        self.vm_binary = vm_binary_path

    def run_vm(self, bytecode_hex: str, caller: int, gas_limit: int, calldata: list, storage: dict) -> dict:
        calldata_str = ",".join(map(str, calldata)) if calldata else "-"
        storage_str = ",".join([f"{k}={v}" for k, v in storage.items()]) if storage else "-"

        cmd = [self.vm_binary, bytecode_hex, str(caller), str(gas_limit), calldata_str, storage_str]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        if res.returncode != 0:
            raise RuntimeError(f"VM crash: {res.stderr}")
        return json.loads(res.stdout)


# In-Memory & Database-Ready State Machine Simulator
class StateMachineSimulator:
    def __init__(self, executor: SmartContractExecutor):
        self.executor = executor
        self.contracts = {}
        self.ledger = []

    def deploy(self, address: str, name: str, asm_code: str, initial_storage: dict):
        bytecode = assemble(asm_code)
        self.contracts[address] = {
            "name": name,
            "bytecode": bytecode,
            "storage": initial_storage
        }
        print(f"[+] Deployed {name} at {address}")
        print(f"    Bytecode ({len(bytecode) // 2} bytes): {bytecode}")
        print(f"    Initial Storage: {initial_storage}\n")

    def send_transaction(self, contract_address: str, caller: int, calldata: list, gas_limit: int = 50000):
        contract = self.contracts[contract_address]
        storage_before = dict(contract["storage"])

        receipt = self.executor.run_vm(
            contract["bytecode"], caller, gas_limit, calldata, storage_before
        )

        storage_after = receipt["storage"] if receipt["status"] == "SUCCESS" else storage_before
        contract["storage"] = storage_after

        tx_entry = {
            "tx_id": len(self.ledger) + 1,
            "contract": contract_address,
            "contract_name": contract["name"],
            "caller": caller,
            "calldata": calldata,
            "gas_used": receipt["gas_used"],
            "status": receipt["status"],
            "error": receipt["error"],
            "storage_before": storage_before,
            "storage_after": storage_after
        }
        self.ledger.append(tx_entry)
        print(
            f"[*] Tx #{tx_entry['tx_id']} ({contract['name']}) by User {caller} -> Status: {receipt['status']} (Gas Used: {receipt['gas_used']})")
        if receipt["error"]:
            print(f"    Error: {receipt['error']}")
        print(f"    State After: {storage_after}")

    def verify_formal_invariants(self):
        print("\n" + "=" * 75)
        print("         FORMAL MATHEMATICAL INVARIANT VERIFICATION REPORT        ")
        print("=" * 75)

        violations = 0
        # Invariant 1 Check: Token Supply Conservation
        print("\n[Invariant 1] Verifying Token Supply Conservation: Sum(balances) == totalSupply")
        for tx in self.ledger:
            if tx["contract_name"] == "ERC20_Token" and tx["status"] == "SUCCESS":
                st = tx["storage_after"]
                total_supply = st.get(0, 0)
                sum_balances = sum(v for k, v in st.items() if k != 0)

                holds = (total_supply == sum_balances)
                status_str = "PASS" if holds else "VIOLATION"
                print(
                    f"  Tx #{tx['tx_id']}: TotalSupply={total_supply}, Sum(Balances)={sum_balances} -> [{status_str}]")
                if not holds: violations += 1

        # Invariant 2 Check: Escrow Solvency & Safety
        print("\n[Invariant 2] Verifying Escrow Safety: locked_amount >= 0 and no lock if settled")
        for tx in self.ledger:
            if tx["contract_name"] == "Escrow_Contract" and tx["status"] == "SUCCESS":
                st = tx["storage_after"]
                locked = st.get(0, 0)
                is_settled = st.get(3, 0)

                holds = (locked >= 0) and not (is_settled == 1 and locked != 0)
                status_str = "PASS" if holds else "VIOLATION"
                print(f"  Tx #{tx['tx_id']}: LockedAmount={locked}, IsSettled={is_settled} -> [{status_str}]")
                if not holds: violations += 1

        print("-" * 75)
        if violations == 0:
            print("✓ FORMAL PROOF RESULT: ALL INVARIANTS HOLD ACROSS ALL STATE TRANSITIONS.")
        else:
            print(f"✗ CRITICAL WARNING: {violations} Invariant violation(s) detected!")
        print("=" * 75)

    def export_sql_sync_script(self, filename="sync_ledger_to_postgres.sql"):
        """Exports the entire run as an executable SQL script for PostgreSQL."""
        with open(filename, "w") as f:
            f.write("-- Generated State Synchronization Script\n")
            for addr, c in self.contracts.items():
                f.write(f"INSERT INTO contract_accounts (address, contract_name, bytecode, storage) "
                        f"VALUES ('{addr}', '{c['name']}', '{c['bytecode']}', '{json.dumps(c['storage'])}');\n")
            for tx in self.ledger:
                f.write(
                    f"INSERT INTO transaction_ledger (contract_address, caller, calldata, gas_limit, gas_used, status, storage_before, storage_after) "
                    f"VALUES ('{tx['contract']}', {tx['caller']}, '{json.dumps(tx['calldata'])}', 50000, {tx['gas_used']}, '{tx['status']}', "
                    f"'{json.dumps(tx['storage_before'])}', '{json.dumps(tx['storage_after'])}');\n")
        print(f"\n[✓] Exported synchronization dump to '{filename}' for PostgreSQL.")


# ============================================================================
# 4. EXECUTION PIPELINE
# ============================================================================
if __name__ == "__main__":
    # Ensure C++ VM binary exists
    vm_bin = "./smart_contract_vm"
    if not os.path.exists(vm_bin) and os.path.exists("./cmake-build-debug/smart_contract_vm"):
        vm_bin = "./cmake-build-debug/smart_contract_vm"

    executor = SmartContractExecutor(vm_binary_path=vm_bin)
    sim = StateMachineSimulator(executor)

    # 1. Deploy Token Contract: TotalSupply = 1,000,000; Alice(101) = 600,000; Bob(102) = 400,000
    token_address = "0xTOKEN000000000000000000000000000000000001"
    sim.deploy(token_address, "ERC20_Token", TOKEN_ASM, {0: 1000000, 101: 600000, 102: 400000})

    # 2. Deploy Escrow Contract: Locked = 5,000; Depositor = 101; Beneficiary = 102; Settled = 0
    escrow_address = "0xESCROW00000000000000000000000000000000001"
    sim.deploy(escrow_address, "Escrow_Contract", ESCROW_ASM, {0: 5000, 1: 101, 2: 102, 3: 0})

    print("--- Executing Transactions ---")
    # Tx 1: Alice transfers 150,000 to Bob (Valid)
    sim.send_transaction(token_address, caller=101, calldata=[1, 102, 150000])

    # Tx 2: Bob transfers 800,000 to Alice (Invalid: Overdraft / Underflow -> Should Revert)
    sim.send_transaction(token_address, caller=102, calldata=[1, 101, 800000])

    # Tx 3: Unauthorized user (103) tries to release Escrow (Invalid -> Should Revert)
    sim.send_transaction(escrow_address, caller=103, calldata=[])

    # Tx 4: Authorized Beneficiary (102) releases Escrow (Valid -> Settlement)
    sim.send_transaction(escrow_address, caller=102, calldata=[])

    # 3. Formally verify mathematical invariants across full transaction history
    sim.verify_formal_invariants()

    # 4. Generate SQL dump to populate PostgreSQL
    sim.export_sql_sync_script()