import cv2
import numpy as np
import os
import shutil
import subprocess
from skimage.metrics import structural_similarity as ssim
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor
from settings import SETTINGS

# Settings


def load_images_and_create_thumbnails(folder, thumbnail_size=(100, 100), thumbnail_ext=".thumb.jpg"):
    thumbnails = []
    file_list = [f for f in os.listdir(folder) if not f.endswith(thumbnail_ext)]  # Exclude thumbnails

    with ThreadPoolExecutor(max_workers=SETTINGS['max_workers']) as executor:
        futures = {executor.submit(create_thumbnail_and_save, folder, filename, thumbnail_size, thumbnail_ext): filename for filename in file_list}

        for future in tqdm(futures, desc="Creating Thumbnails", total=len(file_list)):
            result = future.result()
            if result:
                thumbnails.append(result)
    
    print(f"Loaded {len(thumbnails)} thumbnails from {folder}")
    return thumbnails

def create_thumbnail_and_save(folder, filename, thumbnail_size, thumbnail_ext):
    thumbnail_filename = os.path.splitext(filename)[0] + thumbnail_ext
    thumbnail_path = os.path.join(folder, thumbnail_filename)

    if not os.path.exists(thumbnail_path):
        img = cv2.imread(os.path.join(folder, filename))
        if img is not None:
            thumbnail = create_thumbnail(img, thumbnail_size)
            cv2.imwrite(thumbnail_path, thumbnail)
            set_file_hidden(thumbnail_path)  # Set the thumbnail file to hidden
            return (filename, thumbnail_filename, thumbnail)
    else:
        return (filename, thumbnail_filename, cv2.imread(thumbnail_path))

def create_thumbnail(image, size=(100, 100)):
    thumbnail = cv2.resize(image, size, interpolation=cv2.INTER_AREA)
    return thumbnail

def set_file_hidden(filepath):
    """Set the file attribute to hidden in Windows."""
    subprocess.call(['attrib', '+h', filepath])

def compare_images(imageA, imageB):
    imageA = cv2.cvtColor(imageA, cv2.COLOR_BGR2GRAY)
    imageB = cv2.cvtColor(imageB, cv2.COLOR_BGR2GRAY)
    if SETTINGS['use_gaussian_blur']:
        imageA = cv2.GaussianBlur(imageA, SETTINGS['gaussian_kernel_size'], 0)
        imageB = cv2.GaussianBlur(imageB, SETTINGS['gaussian_kernel_size'], 0)
    score = ssim(imageA, imageB, full=True)[0]
    return score


def compare_images_orb(imageA, imageB):
    orb = cv2.ORB_create()
    kpA, desA = orb.detectAndCompute(imageA, None)
    kpB, desB = orb.detectAndCompute(imageB, None)
    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    matches = bf.match(desA, desB)
    matches = sorted(matches, key=lambda x: x.distance)
    return len(matches)

def group_similar_images(images, threshold=0.5):
    groups = []
    total_images = len(images)
    processed_images = 0

    with ThreadPoolExecutor(max_workers=SETTINGS['max_workers']) as executor:
        with tqdm(total=total_images, desc="Grouping Images") as pbar:
            while images:
                base_image = images.pop(0)
                group = [base_image]
                futures = {executor.submit(compare_images, base_image[2], other_image[2]): other_image for other_image in images}

                for future in futures:
                    score = future.result()
                    other_image = futures[future]
                    if score > threshold:
                        group.append(other_image)
                        images.remove(other_image)
                
                groups.append(group)
                processed_images += 1
                pbar.update(len(group))

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
