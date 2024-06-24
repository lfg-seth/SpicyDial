import os
import random
import tkinter as tk
from PIL import Image, ImageTk, ExifTags
import piexif

# Directory containing images
IMAGE_DIR = r'C:\\Users\\Setheth\\OneDrive - LFG Automotive\\Pictures\\Babygorl'
TARGET_WIDTH = 1920
TARGET_HEIGHT = 1080
BACKGROUND_COLOR = (0, 0, 0)  # Black background

current_index = 0
rating_mode = False

def get_image_rating(image):
    try:
        exif = image._getexif()
        for tag, value in exif.items():
            tag_name = ExifTags.TAGS.get(tag, tag)
            if tag_name == 'Rating':  # Adjust this if your rating is stored differently
                return value
    except (AttributeError, KeyError, IndexError):
        return None

def set_image_rating(image_path, rating):
    img = Image.open(image_path)
    exif_dict = piexif.load(img.info['exif'])
    exif_dict['0th'][piexif.ImageIFD.Rating] = rating
    exif_bytes = piexif.dump(exif_dict)
    img.save(image_path, "jpeg", exif=exif_bytes)

# Load images from the directory and cache them
def load_images():
    images = []
    for file_name in os.listdir(IMAGE_DIR):
        if file_name.lower().endswith(('png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff')):
            img_path = os.path.join(IMAGE_DIR, file_name)
            img = Image.open(img_path)
            width, height = img.size

            if width > height:
                img_orientation = 'landscape'
            elif width < height:
                img_orientation = 'portrait'
            else:
                img_orientation = 'square'

            rating = get_image_rating(img)
            images.append({
                'path': img_path,
                'orientation': img_orientation,
                'rating': rating if rating is not None else 0
            })
            
    return images

# Resize and pad the image to fit the target size with a background color
def resize_and_pad(image, target_width, target_height, background_color):
    width, height = image.size
    image_ratio = width / height
    target_ratio = target_width / target_height

    if image_ratio > target_ratio:
        # Image is wider than target ratio
        new_width = target_width
        new_height = int(target_width / image_ratio)
    else:
        # Image is taller than target ratio
        new_width = int(target_height * image_ratio)
        new_height = target_height

    resized_image = image.resize((new_width, new_height), Image.Resampling.BICUBIC)

    # Create a new image with the background color and paste the resized image onto it
    new_image = Image.new("RGB", (target_width, target_height), background_color)
    paste_position = ((target_width - new_width) // 2, (target_height - new_height) // 2)
    new_image.paste(resized_image, paste_position)

    return new_image

# Filter images based on the spicy scale value
def filter_images(images, spicy_value):
    if 0 <= spicy_value <= 20:
        return [img for img in images if 0 < img['rating'] < 3]
    elif 20 < spicy_value <= 50:
        return [img for img in images if 0 < img['rating'] < 4]
    elif 50 < spicy_value <= 80:
        return [img for img in images if 0 < img['rating'] < 5]
    elif 90 <= spicy_value <= 100:
        return [img for img in images if 0 < img['rating'] > 3]
    return images

# Weighted selection algorithm
def weighted_selection(images, spicy_value):
    filtered_images = filter_images(images, spicy_value)
    if not filtered_images:
        filtered_images = images

    weights = []
    for image in filtered_images:
        rating = image['rating']
        weight = rating * spicy_value / 100  # Higher rating gets more weight as spicy_value increases
        weights.append(weight)
    
    total_weight = sum(weights)
    if total_weight == 0:
        return random.choice(filtered_images)
    
    cumulative_weights = [sum(weights[:i+1]) for i in range(len(weights))]
    r = random.uniform(0, total_weight)
    for i, cw in enumerate(cumulative_weights):
        if r < cw:
            return filtered_images[i]
    return filtered_images[-1]

# Show a single image
def show_image(image_info):
    img_path = image_info['path']
    img = Image.open(img_path)
    img_resized = resize_and_pad(img, TARGET_WIDTH, TARGET_HEIGHT, BACKGROUND_COLOR)
    img_tk = ImageTk.PhotoImage(img_resized)

    panel.config(image=img_tk)
    panel.image = img_tk
    label.config(text=f"{os.path.basename(image_info['path'])} - Orientation: {image_info['orientation']} - Rating: {image_info['rating']}")

# Update the image being displayed
def update_image():
    global slide_show_running
    if slide_show_running:
        spicy_value = scale.get()
        image_to_show = weighted_selection(all_images, spicy_value)
        show_image(image_to_show)
        root.after(3000, update_image)  # Change image every 3 seconds

# Start the slideshow
def start_slideshow():
    global slide_show_running
    slide_show_running = True
    update_image()

# Stop the slideshow
def stop_slideshow():
    global slide_show_running
    slide_show_running = False

# Show the next image
def next_image():
    global current_index
    if rating_mode:
        unrated_images = [img for img in all_images if img['rating'] == 0]
        if unrated_images:
            image_to_show = unrated_images[current_index % len(unrated_images)]
            show_image(image_to_show)
            current_index = (current_index + 1) % len(unrated_images)
        else:
            label.config(text="No more unrated images.")
    else:
        spicy_value = scale.get()
        image_to_show = weighted_selection(all_images, spicy_value)
        show_image(image_to_show)
        current_index = (current_index + 1) % len(all_images)

# Show the previous image (not implemented, just random for now)
def previous_image():
    global current_index
    if rating_mode:
        unrated_images = [img for img in all_images if img['rating'] == 0]
        if unrated_images:
            current_index = (current_index - 1) % len(unrated_images)
            image_to_show = unrated_images[current_index]
            show_image(image_to_show)
        else:
            label.config(text="No more unrated images.")
    else:
        spicy_value = scale.get()
        current_index = (current_index - 1) % len(all_images)
        image_to_show = weighted_selection(all_images, spicy_value)
        show_image(image_to_show)

# Set the rating of the current image
def set_rating(rating):
    global current_index
    if rating_mode:
        unrated_images = [img for img in all_images if img['rating'] == 0]
        if unrated_images:
            img_path = unrated_images[current_index % len(unrated_images)]['path']
            set_image_rating(img_path, rating)
            for img in all_images:
                if img['path'] == img_path:
                    img['rating'] = rating
            next_image()
    else:
        img_path = all_images[current_index]['path']
        set_image_rating(img_path, rating)
        all_images[current_index]['rating'] = rating
        next_image()

# Toggle rating mode
def toggle_rating_mode():
    global rating_mode
    rating_mode = not rating_mode
    if rating_mode:
        label.config(text="Rating Mode: ON")
    else:
        label.config(text="Rating Mode: OFF")
    next_image()

# Setup GUI
root = tk.Tk()
root.geometry(f"{TARGET_WIDTH}x{TARGET_HEIGHT}")
root.title("Photo Viewer")

# Create a frame for the image
image_frame = tk.Frame(root, width=TARGET_WIDTH, height=TARGET_HEIGHT)
image_frame.pack_propagate(False)  # Prevent frame from resizing to fit the image
image_frame.place(x=0, y=0)

panel = tk.Label(image_frame)
panel.pack()

# Controls
controls_frame = tk.Frame(root, bg='black')
controls_frame.place(relx=0.5, rely=0.9, anchor=tk.CENTER)  # Position at the bottom center

btn_previous = tk.Button(controls_frame, text="Previous", command=previous_image)
btn_previous.pack(side=tk.LEFT, padx=5, pady=5)

btn_next = tk.Button(controls_frame, text="Next", command=next_image)
btn_next.pack(side=tk.LEFT, padx=5, pady=5)

btn_play = tk.Button(controls_frame, text="Play", command=start_slideshow)
btn_play.pack(side=tk.LEFT, padx=5, pady=5)

btn_pause = tk.Button(controls_frame, text="Pause", command=stop_slideshow)
btn_pause.pack(side=tk.LEFT, padx=5, pady=5)

btn_toggle_mode = tk.Button(controls_frame, text="Toggle Rating Mode", command=toggle_rating_mode)
btn_toggle_mode.pack(side=tk.LEFT, padx=5, pady=5)

# Rating Buttons
for i in range(1, 6):
    btn = tk.Button(controls_frame, text=str(i), command=lambda i=i: set_rating(i))
    btn.pack(side=tk.LEFT, padx=5, pady=5)

# Spicy Dial, use tkinter scale, 0-100
scale = tk.Scale(controls_frame, label="Spiciness", from_=0, to=100, orient=tk.HORIZONTAL, showvalue=0)
scale.pack(side=tk.LEFT, padx=5, pady=5)

label = tk.Label(controls_frame, text="", bg='black', fg='white')
label.pack(side=tk.LEFT, padx=5, pady=5)

# Bind number keys to set rating
def keypress(event):
    if event.char in '12345':
        set_rating(int(event.char))

root.bind('<KeyPress>', keypress)

# Load images and start the slideshow
all_images = load_images()
random.shuffle(all_images)
slide_show_running = False

# Show the first image
if all_images:
    show_image(all_images[0])

root.mainloop()

