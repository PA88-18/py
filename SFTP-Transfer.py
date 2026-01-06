#!/usr/bin/python3.9
import os
import logging
import paramiko
import subprocess
import sys
from datetime import datetime
sys.path.append('#path-to-vault-functions-directory#')
from VaultFunctions import *

#PATH Set
os.environ["PATH"] = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

#Vault Params
vaultToken = GetVaultToken()
vaultEngine = ""
vaultPath = ""
vaultReturn = GetVaultSecretAllIDs(vaultToken, vaultEngine, vaultPath)

#Vault Return into Variables

apgp = vaultReturn.get("")
exportsshpass = vaultReturn.get("")
recip = vaultReturn.get("")
pgpkeypass = vaultReturn.get("")

# Setup parameters
DATE = datetime.now().strftime("%Y%m%d-%H%M%S")

# Directories and file paths
DIR_INPUT = "/sftp/inbound/"
DIR_ARCHIVE = f"{DIR_INPUT}/archive"
DIR_LOGGING = "/admin/logging/log"
LOGFILEMASK = "FILEMASK"
LOG_FILENAME = f"{DIR_LOGGING}/{LOGFILEMASK}-{DATE}.log"

REMOTE_SERVER = "server.com"
REMOTE_DIRECTORY = "Inbound/"
SFTP_KEY = "/admin/keys"
USER_NAME = "USER"
FILE_MASK = "USER.FILEMASK"
RECIP = recip
PGP = apgp
SSHPASS = exportsshpass
PGPKEY = pgpkeypass

#Configure Logging
logging.basicConfig(filename=LOG_FILENAME, level=logging.INFO, format="%(asctime)s - %(message)s")

logging.info("===========================================")
logging.info("=================BEGIN=====================")
logging.info("===========================================")

def encrypt_file(input_file, output_file, recipient, signer, pgpkeypass):
    command = [
        "/usr/bin/gpg",
        "--batch", 
        "--yes",
        "--pinentry-mode", "loopback",
        "--always-trust",
        "--recipient", recipient,
        "-u", signer,
        "--passphrase", pgpkeypass,
        "-o", output_file,
        "--encrypt", "--sign", input_file
    ]
    subprocess.run(command)

def send_file(local_file, server, username, private_key_path, remote_directory, local_directory):

    try:
        logging.info("Connecting to SFTP server")
        # Load private key
        private_key = paramiko.RSAKey.from_private_key_file(private_key_path, password=exportsshpass)

        # Establish SSH transport
        transport = paramiko.Transport((server, 22))
        transport.connect(username=username, pkey=private_key)

        # Create SFTP client
        sftp = paramiko.SFTPClient.from_transport(transport)

        # Navigate to the appropriate remote directory
        sftp.chdir("/")  # Start at root
        for folder in remote_directory.split("/"):
            if folder:  # Avoid empty strings
                sftp.chdir(folder)

        # Set local directory
        os.chdir(local_directory)

        # Upload the file
        sftp.put(local_file, os.path.join(sftp.getcwd(), os.path.basename(local_file)))
        logging.info(f"File {local_file} successfully sent to {server}:{remote_directory}")

    except Exception as e:
        logging.error(f"An error occurred: {e}")
    finally:
        # Close connections
        try:
            sftp.close()
        except:
            pass
        try:
            transport.close()
        except:
            pass


def archive_file(original, archive_path):
    os.rename(original, archive_path)
    os.chown(archive_path, 0, 0)  # Set owner to root
    os.chmod(archive_path, 0o600)  # Set permissions to 600

# Main routine
logging.info("Start")

transfer_files = [
    os.path.join(DIR_INPUT, f) for f in os.listdir(DIR_INPUT)
    if f.startswith(FILE_MASK) and not f.endswith("pgp")
]

for transfer_file in transfer_files:
    logging.info(f"Found {transfer_file}")

    file_base = os.path.splitext(os.path.basename(transfer_file))[0]
    encrypted_file = f"{DIR_INPUT}/{file_base}.pgp"
    sftp_file = f"/admin/tmp/SFTP-{file_base}-{DATE}.sftp"
    archive_path_txt = f"{DIR_ARCHIVE}/{file_base}-{DATE}.txt"
    archive_path_pgp = f"{DIR_ARCHIVE}/{file_base}-{DATE}.pgp"


    logging.info(f"Encrypting {transfer_file}")
    encrypt_file(transfer_file, encrypted_file, RECIP, PGP, PGPKEY)

    logging.info(f"Sending {encrypted_file}")
    send_file(encrypted_file, REMOTE_SERVER, USER_NAME, SFTP_KEY, REMOTE_DIRECTORY, DIR_INPUT)
    #send_file(local_file, server, username, private_key_path, remote_directory, local_directory)

    logging.info(f"Archiving {transfer_file} and {encrypted_file}")
    archive_file(transfer_file, archive_path_txt)
    archive_file(encrypted_file, archive_path_pgp)

logging.info("End")