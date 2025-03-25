import subprocess
import json
from packaging import version

LAMBDA_PYTHON_38_PACKAGES = {
    'beautifulsoup4': '4.11.2',
    'requests': '2.28.2',
    'Flask': '2.2.3',
    'Werkzeug': '2.2.3',
    'click': '8.1.3',
    'blinker': '1.5',
    'itsdangerous': '2.1.2',
    'Jinja2': '3.1.2',
    'MarkupSafe': '2.1.2',
    'urllib3': '1.26.15',
    'certifi': '2022.12.7',
    'charset-normalizer': '3.1.0',
    'idna': '3.4',
    'soupsieve': '2.4',
    'setuptools': '65.5.1',
    'pip': '22.3.1',
    'tls-client': '0.2',
    'cryptography': '39.0.1',
    'pyOpenSSL': '23.1.1',
    'lxml': '4.9.2',
}

def simplify_requirements():
    # Read current requirements
    with open('requirements.txt', 'r') as f:
        requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]

    # Keep only essential packages and their Lambda-compatible versions
    essential_packages = [
        'beautifulsoup4',
        'requests',
        'Flask',
        'tls-client',
        'lxml',
        'cryptography',
    ]

    simplified_reqs = []
    for pkg in essential_packages:
        if pkg in LAMBDA_PYTHON_38_PACKAGES:
            simplified_reqs.append(f"{pkg}=={LAMBDA_PYTHON_38_PACKAGES[pkg]}")
        else:
            # For packages not in the known list, keep them but warn
            print(f"⚠️ Warning: {pkg} not in known Lambda packages")
            matching = [r for r in requirements if r.startswith(f"{pkg}==")]
            if matching:
                simplified_reqs.append(matching[0])
            else:
                simplified_reqs.append(pkg)

    # Write simplified requirements
    with open('requirements.txt', 'w') as f:
        f.write('\n'.join(simplified_reqs))
    
    print("\n✅ Updated requirements.txt with Lambda-compatible versions")
    print("\nNew requirements:")
    print('\n'.join(simplified_reqs))

if __name__ == "__main__":
    simplify_requirements() 