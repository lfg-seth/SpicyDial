import os
import shutil
from tqdm import tqdm
from settings import SETTINGS

def clean_grouped_folders(grouped_folder, original_folder, thumbnail_ext=".thumb"):
    for group_name in tqdm(os.listdir(grouped_folder), desc="Cleaning Groups"):
        group_path = os.path.join(grouped_folder, group_name)
        if not os.path.isdir(group_path):
            continue

        for filename in os.listdir(group_path):
            file_path = os.path.join(group_path, filename)
            if filename.endswith(thumbnail_ext):
                # Check for corresponding full-size photo
                original_filename = filename.replace(thumbnail_ext, '')
                original_file_path = os.path.join(group_path, original_filename)
                if not os.path.exists(original_file_path):
                    # Delete orphaned thumbnail
                    os.remove(file_path)
                    print(f"Deleted orphaned thumbnail: {file_path}")
            else:
                # Check for corresponding thumbnail
                thumbnail_filename = os.path.splitext(filename)[0] + thumbnail_ext
                thumbnail_file_path = os.path.join(group_path, thumbnail_filename)
                if not os.path.exists(thumbnail_file_path):
                    # Print warning about missing thumbnail (optional)
                    print(f"Warning: Missing thumbnail for {file_path}")

        # Move remaining files back to the original folder
        for filename in os.listdir(group_path):
            src = os.path.join(group_path, filename)
            dst = os.path.join(original_folder, filename)
            shutil.move(src, dst)
            print(f"Moved {filename} back to {original_folder}")

        # Remove empty group folder
        os.rmdir(group_path)
        print(f"Removed empty group folder: {group_path}")

def main():
    grouped_folder = SETTINGS['output_folder']
    original_folder = SETTINGS['folder_path']
    
    clean_grouped_folders(grouped_folder, original_folder)

if __name__ == "__main__":
    main()
