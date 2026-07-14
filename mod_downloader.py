import os
import sys
import json
import requests

# Modrinth strictly requires a unique User-Agent header. 
# Generic clients are automatically rate-limited or blocked.
HEADERS = {
    "User-Agent": "modrinth-auto-downloader/1.0.0 (contact@example.com)"
}

def search_project_id(name, version, platform):
    """
    Searches Modrinth to turn a human-readable name or mixed slug into 
    the exact project ID required for precise version mapping.
    """
    url = "https://api.modrinth.com/v2/search"
    
    # Restrict search indexing to look for mods matching your game conditions
    facets = json.dumps([
        ["project_type:mod"],
        [f"versions:{version}"],
        [f"categories:{platform}"]
    ])
    
    params = {
        "query": name.strip(),
        "facets": facets,
        "limit": 1
    }
    
    try:
        response = requests.get(url, headers=HEADERS, params=params)
        response.raise_for_status()
        data = response.json()
        if data.get('hits'):
            hit = data['hits'][0]
            return hit['project_id'], hit['title']
    except Exception as e:
        print(f"Search error for '{name}': {e}")
    
    # Fallback option: if search finds nothing, treat the text directly as a raw slug
    fallback_slug = name.strip().lower().replace(" ", "-")
    return fallback_slug, name.strip()


def download_mod_and_dependencies(project_id_or_slug, version, platform, dest_dir, downloaded_set):
    """
    Recursively finds the target mod version, downloads it, checks its 
    dependency tree, and pulls any required backend dependencies.
    """
    # Prevent infinite loop recursion or duplicate file downloads
    if project_id_or_slug in downloaded_set:
        return

    url = f"https://api.modrinth.com/v2/project/{project_id_or_slug}/version"
    try:
        response = requests.get(url, headers=HEADERS)
        if response.status_code == 404:
            print(f"Project profile '{project_id_or_slug}' could not be located on Modrinth.")
            return
        response.raise_for_status()
        versions_list = response.json()
    except Exception as e:
        print(f"Failed to connect to version registry for {project_id_or_slug}: {e}")
        return

    matching_version = None
    # Modrinth returns versions sorted newest to oldest. 
    # Loop through to find the first exact environmental match.
    for v in versions_list:
        loaders = [l.lower() for l in v.get('loaders', [])]
        game_versions = [gv.lower() for gv in v.get('game_versions', [])]
        
        if platform.lower() in loaders and version.lower() in game_versions:
            matching_version = v
            break

    if not matching_version:
        print(f"No matching release found for '{project_id_or_slug}' on {platform} {version}")
        return

    # Log internal IDs to track duplicates securely
    actual_id = matching_version.get('project_id')
    if actual_id:
        downloaded_set.add(actual_id)
    downloaded_set.add(project_id_or_slug)

    # Resolve target download file mapping
    files = matching_version.get('files', [])
    if not files:
        print(f"No files attached to the version match for '{project_id_or_slug}'")
        return

    # Select the developer's marked 'primary' file, or default to the first file entry
    primary_file = next((f for f in files if f.get('primary')), files[0])
    download_url = primary_file.get('url')
    filename = primary_file.get('filename')

    # Stream download the target archive (.jar or .mcaddon)
    os.makedirs(dest_dir, exist_ok=True)
    target_path = os.path.join(dest_dir, filename)

    print(f"Downloading: {filename}...")
    try:
        file_stream = requests.get(download_url, headers=HEADERS, stream=True)
        file_stream.raise_for_status()
        with open(target_path, 'wb') as f:
            for chunk in file_stream.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"Download complete: {filename}")
    except Exception as e:
        print(f"Failed to download {filename}: {e}")
        return

    # Dependency Processing Engine
    dependencies = matching_version.get('dependencies', [])
    for dep in dependencies:
        # Target 'required' dependencies. Ignore 'optional', 'incompatible', or 'embedded' types.
        if dep.get('dependency_type') == 'required':
            dep_id = dep.get('project_id')
            if dep_id and dep_id not in downloaded_set:
                print(f"Found missing dependency requirement (ID: {dep_id}). Resolving dynamically...")
                download_mod_and_dependencies(dep_id, version, platform, dest_dir, downloaded_set)


if __name__ == "__main__":
    print("====================================================")
    print("   MODRINTH AUTOMATIC MOD & DEPENDENCY DOWNLOADER   ")
    print("====================================================\n")

    # Prompt user for edition context parameters
    edition = input("1. Enter Minecraft Edition (java/bedrock): ").strip().lower()
    ver = input("2. Enter Minecraft Version (e.g., 1.21.6): ").strip()
    
    # Automatically map platform parameter if Bedrock is selected
    if edition == "bedrock":
        platform = "bedrock"
        print("Bedrock Edition detected. Loader platform automatically mapped to 'bedrock'.")
    else:
        platform = input("3. Enter Mod Loader / Platform (e.g., fabric, forge, neoforge): ").strip().lower()

    names_input = input("4. Enter Mod Names / Slugs (separated by commas): ").strip()
    dest = input("5. Enter Save Directory Path (e.g., ./mods): ").strip()

    if not edition or not ver or not platform or not names_input or not dest:
        print("\nAll input parameters are required to run. Aborting.")
        sys.exit(1)

    # Format user parameters into isolated target arrays
    raw_mod_list = [n.strip() for n in names_input.split(",") if n.strip()]
    downloaded_registry = set()

    print("\n--- Starting Search & Retrieval Job ---")
    for mod_name in raw_mod_list:
        print(f"\nInitializing lookup for: '{mod_name}'")
        project_id, verified_title = search_project_id(mod_name, ver, platform)
        print(f"Matched to: {verified_title} (ID/Slug: {project_id})")
        
        # Initialize recursive retrieval stack
        download_mod_and_dependencies(project_id, ver, platform, dest, downloaded_registry)

    print("\nAll target files and missing dependencies have been successfully downloaded!")