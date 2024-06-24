import cv2
import numpy as np
import os
import shutil
import subprocess
from skimage.metrics import structural_similarity as ssim
from tqdm import tqdm

# Settings
SETTINGS = {
    'folder_path': r'C:\\Users\\Setheth\\OneDrive - LFG Automotive\\Pictures\\Babygorl',
    'output_folder': r'C:\\Users\\Setheth\\OneDrive - LFG Automotive\\Pictures\\Babygorl\\Grouped',
    'thumbnail_size': (200, 200),
    'thumbnail_ext': '.thumb.jpg',
    'ssim_threshold': 0.4,
}

def load_images_and_create_thumbnails(folder, thumbnail_size=(200, 200), thumbnail_ext=".thumb.jpg"):
    thumbnails = []
    file_list = [f for f in os.listdir(folder) if not f.endswith(thumbnail_ext)]  # Exclude thumbnails
    for filename in tqdm(file_list, desc="Creating Thumbnails"):
        thumbnail_filename = os.path.splitext(filename)[0] + thumbnail_ext
        thumbnail_path = os.path.join(folder, thumbnail_filename)
        
        if not os.path.exists(thumbnail_path):
            img = cv2.imread(os.path.join(folder, filename))
            if img is not None:
                thumbnail = create_thumbnail(img, thumbnail_size)
                cv2.imwrite(thumbnail_path, thumbnail)
                set_file_hidden(thumbnail_path)  # Set the thumbnail file to hidden
                thumbnails.append((filename, thumbnail_filename, thumbnail))
        else:
            thumbnails.append((filename, thumbnail_filename, cv2.imread(thumbnail_path)))
    print(f"Loaded {len(thumbnails)} thumbnails from {folder}")
    return thumbnails

def create_thumbnail(image, size=(200, 200)):
    thumbnail = cv2.resize(image, size, interpolation=cv2.INTER_AREA)
    return thumbnail

def set_file_hidden(filepath):
    """Set the file attribute to hidden in Windows."""
    subprocess.call(['attrib', '+h', filepath])

def compare_images(imageA, imageB):
    # Convert images to grayscale
    grayA = cv2.cvtColor(imageA, cv2.COLOR_BGR2GRAY)
    grayB = cv2.cvtColor(imageB, cv2.COLOR_BGR2GRAY)
    # Compute SSIM between two images
    score, diff = ssim(grayA, grayB, full=True)
    return score

def group_similar_images(images, threshold=0.4):
    groups = []
    total_images = len(images)
    processed_images = 0
    for base_image in tqdm(images.copy(), desc="Grouping Images"):
        if base_image not in images:
            continue
        images.remove(base_image)
        group = [base_image]
        for other_image in images[:]:
            score = compare_images(base_image[2], other_image[2])
            if score > threshold:
                group.append(other_image)
                images.remove(other_image)
        groups.append(group)
        processed_images += 1
    return groups

def move_images_to_groups(groups, base_folder, src_folder, thumbnail_ext=".thumb.jpg"):
    if not os.path.exists(base_folder):
        os.makedirs(base_folder)
    
    for i, group in enumerate(tqdm(groups, desc="Moving Images to Groups")):
        if len(group) > 1:  # Only move if there is more than one photo in the group
            group_folder = os.path.join(base_folder, f"group_{i+1}")
            if not os.path.exists(group_folder):
                os.makedirs(group_folder)
            
            for j, image in enumerate(group):
                src_img = os.path.join(src_folder, image[0])
                dst_img = os.path.join(group_folder, image[0])
                shutil.move(src_img, dst_img)
                
                src_thumb = os.path.join(src_folder, image[1])
                dst_thumb = os.path.join(group_folder, image[1])
                shutil.move(src_thumb, dst_thumb)
                set_file_hidden(dst_thumb)  # Ensure the moved thumbnail is hidden
                
                print(f"Moved {image[0]} and {image[1]} to {group_folder}")

def clean_grouped_folders(grouped_folder, original_folder, thumbnail_ext=".thumb.jpg"):
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
            if filename.endswith(thumbnail_ext):
                set_file_hidden(dst)  # Ensure the moved thumbnail is hidden
            print(f"Moved {filename} back to {original_folder}")

        # Remove empty group folder
        os.rmdir(group_path)
        print(f"Removed empty group folder: {group_path}")

def main():
    folder_path = SETTINGS['folder_path']
    output_folder = SETTINGS['output_folder']
    thumbnail_size = SETTINGS['thumbnail_size']
    thumbnail_ext = SETTINGS['thumbnail_ext']
    ssim_threshold = SETTINGS['ssim_threshold']
    
    # Load images and create thumbnails
    thumbnails = load_images_and_create_thumbnails(folder_path, thumbnail_size, thumbnail_ext)
    
    # Group similar thumbnails
    grouped_images = group_similar_images(thumbnails, ssim_threshold)

    # Print grouped images
    for i, group in enumerate(grouped_images):
        print(f"Group {i+1}:")
        for j, image in enumerate(group):
            print(f"  {j}: {image[0]}")
    
    # Move images to group folders
    move_images_to_groups(grouped_images, output_folder, folder_path, thumbnail_ext)

    # Clean grouped folders and move files back to original folder
    # clean_grouped_folders(output_folder, folder_path, thumbnail_ext)

if __name__ == "__main__":
    main()
