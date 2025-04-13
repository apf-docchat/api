import time


def generate_data():
    content = """
    Title: Examining the Impact of Workplace Accidents on Employee Safety and Productivity\n\n
    Introduction:\n
    Workplace accidents remain a significant concern across industries, impacting employee safety, morale, and overall productivity. Despite advancements in safety protocols and regulations, incidents still occur, highlighting the need for continued vigilance and improvement in safety measures. This article explores the various facets of workplace accidents, their causes, consequences, and strategies for prevention.\n\n
    Causes of Workplace Accidents:\n
    Several factors contribute to workplace accidents, ranging from human error to equipment malfunction. Lack of proper training, fatigue, and negligence are common human-related causes, while inadequate maintenance, faulty machinery, and environmental hazards represent equipment-related factors. Additionally, workplace culture and organizational practices can influence safety outcomes, with poor communication, rushed deadlines, and disregard for safety protocols exacerbating risks.\n
    """
    words = content.split()
    chunk_size = 5  # Number of words to include in each chunk
    # Initialize an empty string to accumulate words
    current_chunk = ""

    for word in words:
        # Add the current word to the chunk
        current_chunk += word + " "

        # Check if the current chunk has reached the chunk size
        if len(current_chunk.split()) >= chunk_size:
            # Stream the current chunk as a continuous string
            yield f"data: {current_chunk.strip()}\n\n"
            # Reset the current chunk to empty for the next set of words
            current_chunk = ""
            # Pause briefly before sending the next chunk
            time.sleep(0.5)

    # After looping through all words, check if there's a remaining chunk to send
    if current_chunk:
        yield f"data: {current_chunk.strip()}\n\n"

    # Signal the end of the stream
    yield "event: finalOutput\ndata: End of Streaming\n\n"
