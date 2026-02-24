import os
import json
import hashlib
import zipfile
from datetime import datetime
from pathlib import Path

def calculate_sha256(filepath):
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def package_dataset():
    base_dir = Path(__file__).resolve().parent.parent
    multi_probe_dir = base_dir / "results" / "mersenne" / "multi_probe"
    dist_dir = base_dir / "results" / "mersenne" / "dist"
    
    os.makedirs(dist_dir, exist_ok=True)
    
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    dataset_name = f"OEDA_Mersenne_Dataset_300B_{timestamp}"
    zip_path = dist_dir / f"{dataset_name}.zip"
    manifest_path = dist_dir / f"artifact_manifest_{timestamp}.json"
    ledger_path = dist_dir / "ledger.jsonl"
    license_path = base_dir / "results" / "mersenne" / "DATASET_LICENSE.md"

    # 1. Encontrar telemetrías
    json_files = list(multi_probe_dir.glob("telemetry_sonda_*.json"))
    if not json_files:
        print("[!] No se encontraron archivos de telemetría para empaquetar.")
        return

    # 2. Comprimir datos
    file_records = []
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        if license_path.exists():
            zf.write(license_path, arcname="DATASET_LICENSE.md")
            
        for jf in json_files:
            zf.write(jf, arcname=f"telemetry/{jf.name}")
            file_records.append({
                "filename": jf.name,
                "size_bytes": os.path.getsize(jf),
                "sha256": calculate_sha256(jf)
            })
            
    # 3. Calcular Checksum del Zip Maestro
    zip_size = os.path.getsize(zip_path)
    zip_sha256 = calculate_sha256(zip_path)
    
    # 4. Crear Manifest (Check S3)
    manifest = {
        "dataset_name": dataset_name,
        "built_at_utc": datetime.utcnow().isoformat(),
        "total_files": len(file_records),
        "total_simulated_exponents_claimed": 250000000000,
        "origin": "SIMULATED (Software Stress-Test)",
        "master_archive": {
            "file": zip_path.name,
            "size_bytes": zip_size,
            "sha256": zip_sha256
        },
        "components": file_records
    }
    
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=4)
        
    # 5. Anexar al Ledger
    ledger_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "event": "DATASET_PACKAGED",
        "dataset": dataset_name,
        "manifest_sha256": calculate_sha256(manifest_path),
        "archive_sha256": zip_sha256,
        "parameters": {
            "start_p": 50000000000,
            "end_p": 300000000000,
            "seed_check_S1": "NON-DETERMINISTIC STRICT (Time-based fallback used)"
        }
    }
    
    with open(ledger_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(ledger_entry) + "\n")
        
    print(f"[+] DATASET EMPAQUETADO EXITOSAMENTE.")
    print(f"    - Archivo: {zip_path}")
    print(f"    - Manifiesto: {manifest_path}")
    print(f"    - SHA256: {zip_sha256}")

if __name__ == "__main__":
    package_dataset()
