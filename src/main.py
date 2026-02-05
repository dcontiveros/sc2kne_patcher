import hashlib
import requests
import os
import sys
import pycdlib
import shutil
import is3extract
from pathlib import Path
from urllib.parse import urlparse, unquote
# local files
from patch_sc2k_v11 import patch_v11

def get_project_paths():
    """Calculates paths relative to this script's location."""
    base_dir = Path(__file__).resolve().parent.parent
    return {
        "root": base_dir,
        "files": base_dir / "files",
        "sig_file": base_dir / "files" / "md5sum.txt"
    }

def calculate_md5(file_path):
    """Helper to handle the heavy lifting of hashing."""
    md5_hash = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            md5_hash.update(chunk)
    return md5_hash.hexdigest()

def map_directory_hashes(directory_path, ignore_file):
    """Pure function: takes a path and returns a map of hashes."""
    hash_map = {}

    if not directory_path.exists():
        return hash_map

    for file_path in directory_path.iterdir():
        if file_path.is_file() and file_path.name != ignore_file:
            # We could move the actual hashing to its own helper too
            file_hash = calculate_md5(file_path)
            hash_map[file_hash] = file_path.name

    return hash_map

def load_signature_hashes(sig_path):
    """
    Reads the md5sum.txt file and returns a list of the
    expected MD5 hashes (the first column).
    """
    expected_hashes = []

    if not sig_path.exists():
        print(f"⚠️ Warning: {sig_path.name} not found.")
        return expected_hashes

    with open(sig_path, "r", encoding="utf-8") as f:
        for line in f:
            # Strip whitespace and ignore empty lines
            clean_line = line.strip()
            if not clean_line:
                continue

            # Split by whitespace: [hash, filename...]
            parts = clean_line.split()
            if parts:
                expected_hashes.append(parts[0])

    return expected_hashes

def file_checks(current_files, expected_hashes):
    """
    This function performs all file checking for patcher
    """
    # We need 2 files only, ISO and UPDATE
    if len(current_files) < 2:
        print("FILE QTY CHECK FAILED ❌")
        print()
        return False

    # Now we do some md5sum comparison. The files could be named something else so we only go by md5
    for hash in expected_hashes:
        if hash not in current_files:
            print(f"MD5sum {hash} MISSING ❌")
            print()
            return False

    # if all checks pass, return True
    return True

def download_binary_file(url, folder_path):
    '''
    Downloads binary files, sanitizes URL encoding (like %20),
    and displays a live MB counter.
    '''
    try:
        # 1. Extract and sanitize filename (converts %20 to spaces, etc.)
        raw_path = urlparse(url).path
        filename = unquote(Path(raw_path).name)

        if not filename:
            print("Error: URL does not contain a valid filename.")
            return False

        # 2. Setup path and ensure directory exists
        path = Path(folder_path) / filename
        path.parent.mkdir(parents=True, exist_ok=True)

        # 3. Stream the download to keep memory usage low
        with requests.get(url, stream=True) as response:
            response.raise_for_status()

            total_dl = 0
            with path.open('wb') as file:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        file.write(chunk)
                        total_dl += len(chunk)
                        # \r keeps the output on a single line
                        print(f"\rProgress: {total_dl / (1024*1024):.2f} MB downloaded", end="")

            print(f"\nSuccessfully saved to: {path.absolute()}")
            return True

    except requests.exceptions.RequestException as e:
        print(f"\nDownload failed: {e}")
        return False


def extract_iso_recursive(iso_path, iso_internal_folder, local_dest_root):
    '''
    Extract directory on ISO and its contents, including subdirs
    '''
    iso = pycdlib.PyCdlib()
    iso.open(iso_path)

    # Standardize the internal path (e.g., /2KNET)
    iso_dir = f"/{iso_internal_folder.strip('/')}"
    local_root = Path(local_dest_root) / iso_internal_folder.strip('/')

    def walk_and_extract(current_iso_dir, current_local_dir):
        current_local_dir.mkdir(parents=True, exist_ok=True)

        for child in iso.list_children(iso_path=current_iso_dir):
            # Skip ISO 9660 dot entries
            name = child.file_identifier().decode('utf-8').split(';')[0]
            if name in ['.', '..']:
                continue

            # Full paths for ISO and Local
            child_iso_path = f"{current_iso_dir}/{child.file_identifier().decode('utf-8')}"
            child_local_path = current_local_dir / name

            if child.is_dir():
                # Recursive call for folders
                walk_and_extract(child_iso_path, child_local_path)
            else:
                # Extraction for files
                print(f"Extracting: {name}")
                with open(child_local_path, 'wb') as f:
                    iso.get_file_from_iso_fp(f, iso_path=child_iso_path)

    try:
        walk_and_extract(iso_dir, local_root)
        print(f"\nSuccess! Extracted to: {local_root.absolute()}\n")

    finally:
        iso.close()


def check_updated_game_files(updater_files, path):
    '''
    Does a final check of the md5sum in the game directory
    '''
    print("Checking updater MD5sums ...")
    for key in updater_files.keys():
        file_path = path / key
        if calculate_md5(file_path) == updater_files.get(key):
            print(f"{key} - PASSED MD5 CHECK ✅")
        else:
            print(f"{key} - FAILED MD5 CHECK ❌")
            return False
    return True

def main():
    """
    Simple main function. Logic is as follows:
    1. Read in file hashs an
    2. Perform shasum for testing
    3. Extract/Update game client and server
    4. Interopability patch
    5. User Experience patch (click4dyman)
    """
    # get paths
    paths = get_project_paths()
    urls = {
            "iso-page": "https://archive.org/details/simcity2000networkedition",
            "patch-page": "https://archive.org/details/update2knet11",
            "iso-direct": "https://archive.org/download/simcity2000networkedition/Simcity%202000%20Network%20Edition.iso",
            "patch-direct": "https://archive.org/download/update2knet11/update2knet11.exe"
           }

    # MD5sums for extracted files
    updater_files = {
        "2KCLIENT.EXE": "9942b057f14fa995cfe8d710e6c1b9bf" ,
        "2KSERVER.EXE": "6c412cf27726879aaa97d75db857a601" ,
        "USAHORES.DLL": "a3cf6380bf74df2e8e266122f3bfa276" ,
        "USARES.DLL": "05b105b841e3fe34fe7f37cae67b6d74"
   }

    print("╔══════════════════════════════════════════╗")
    print("║  Simcity 2000: Network Edition patcher   ║")
    print("╚══════════════════════════════════════════╝")

    print("This program will retrieve/patch everything needed to get this game running on modern Windows.")
    print()

    # Start of file checks
    print("Checking for required files ...")
    print()
    # Here we should just get all the files into a dict. We will need them later
    current_files = map_directory_hashes(paths['files'], ignore_file="md5sum.txt")

    # Get all md5sums
    expected_hashes = load_signature_hashes(paths['sig_file'])

    # individual checks. We need result to be true prior to running extractors and patchers
    file_check_result = file_checks(current_files, expected_hashes)

    # We only want a True result to continue here
    if file_check_result == False:
        print("The installer did not find all the required files.")
        print("To continue offline, grab the files from the following URLs and place them in the files directory:")
        print(f"ISO: {urls.get("iso-page")}")
        print(f"1.1 Patch: {urls.get("patch-page")}")
        print("This patcher can grab the required files. Would you like to retrieve the files?")
        choice = input("Enter Y/N: ")
        if choice.lower() != 'y':
            print("Rerun this script once files with matching md5sums are in the files directory")
            sys.exit(0)
        else:
            print("Retrieving files ...")
            download_binary_file(urls.get("iso-direct"),paths['files'])
            print()
            download_binary_file(urls.get("patch-direct"),paths['files'])

            # repopulate current files and check once more
            current_files = map_directory_hashes(paths['files'], ignore_file="md5sum.txt")
            file_check_result = file_checks(current_files, expected_hashes)
            if file_check_result == False:
                print(f"DOWNLOAD FAILED ❌")
                print("Please check the above URLs.")
                sys.exit(0)
            print()

    # If we make it here all checks passed
    print("FILE CHECKS PASSED ✅")

    # insert iso and patch into paths dict
    iso_filename = current_files.get("a6ad08f1b2d53045e18beb4c1a5da846")
    update_filename = current_files.get("2c3ccac00e8410d73cbea858b9d25159")
    paths['iso_file'] = paths['files'] / iso_filename
    paths['update_file'] = paths['files'] / update_filename
    paths['update_dir'] = paths['files'] / "update"
    # Extract files from original ISO
    print("Extracting relevant ISO contents to 2KNET directory")
    extract_iso_recursive( paths['iso_file'] ,  "2KNET", paths['files'])

    # Now we have to extract the patched version
    print("Extracting updater files ... ")
    # Here
    paths['update_dir'].mkdir(parents=True, exist_ok=True)
    # read in updater
    with open( paths['update_file'] ,'rb') as f:
        data = f.read()

    # Get all archives in IS3 file
    archives = is3extract.find_is3_archives(data)
    is3extract.extract_archive(data, archives[1], paths['update_dir'])

    # Now we replace the updater files. Copy will use keys in dict
    # specify 2KNET folder
    paths["game_dir"] = paths["files"] / "2KNET"


    for key in updater_files.keys():
        # We replacee the file in 2KNET with the updater files
        # Source/Target
        source = paths["update_dir"] / key
        target = paths["game_dir"] / key
        if source.exists():
            shutil.copy2(source, target)
            print(f"Successfully overwrote {target.name} with {source.name}")
        else:
            print(f"Error: Source file {source} not found.")

    # now we check final md5sums
    game_final_check = check_updated_game_files(updater_files, paths["game_dir"])

    # bomb out if check failes
    if game_final_check == False:
        print("EXTRACTION FAILED! OPEN AN ISSUE ON GITHUB ❌")
        sys.exit(0)

    # Start patching here
    print("\nSimcity 2000: Network Edition extraction successful.")
    print("We will now patch the game to allow a seamless run on modern Windows systems.")

    # run patch
    success, details = patch_v11(paths['game_dir'], quiet=True)

    # Verify MD5 matches
    if details['server']['md5'] == details['server']['expected_md5']:
        print("SERVER PATCHES VERIFIED ✅")
    else:
        print("PATCHING FAILED. OPEN A TICKET ON GITHUB ❌")

    print("This ends the patching. You should now be able to launch the patched version inside the 2KNET directory.")
    print("Use the executable ending in -v11.")


if __name__ == "__main__":
    main()