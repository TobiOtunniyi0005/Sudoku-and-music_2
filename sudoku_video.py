import random
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, FFMpegWriter
from matplotlib.patches import Rectangle
from moviepy.video.io.VideoFileClip import VideoFileClip
from moviepy.audio.io.AudioFileClip import AudioFileClip
import os

MUSIC_FILE = "background_music.mp3"  

FPS = 30
FRAMES_PER_STATE = 25   # ~0.8 sec per step. Increase for slower, decrease for faster video.
REMOVE_COUNT = 40       # ~41 clues = nice easy puzzle solvable with naked singles only

def is_valid(board, row, col, num):
    # Row
    for x in range(9):
        if board[row][x] == num:
            return False
    # Column
    for x in range(9):
        if board[x][col] == num:
            return False
    # Box
    start_row = row // 3 * 3
    start_col = col // 3 * 3
    for i in range(3):
        for j in range(3):
            if board[i + start_row][j + start_col] == num:
                return False
    return True

def solve(board):
    """Standard backtracking to create a full solved board"""
    for i in range(9):
        for j in range(9):
            if board[i][j] == 0:
                for num in range(1, 10):
                    if is_valid(board, i, j, num):
                        board[i][j] = num
                        if solve(board):
                            return True
                        board[i][j] = 0
                return False
    return True

def update_candidates(candidates, row, col, num):
    """Remove num from all peers (row, col, box)"""
    for j in range(9):
        if j != col:
            candidates[row][j].discard(num)
    for i in range(9):
        if i != row:
            candidates[i][col].discard(num)
    br = (row // 3) * 3
    bc = (col // 3) * 3
    for i in range(3):
        for j in range(3):
            rr = br + i
            cc = bc + j
            if rr != row or cc != col:
                candidates[rr][cc].discard(num)

def initialize_candidates(board):
    """Create candidate sets for every empty cell"""
    candidates = [[set(range(1, 10)) if board[i][j] == 0 else set() for j in range(9)] for i in range(9)]
    for i in range(9):
        for j in range(9):
            if board[i][j] != 0:
                update_candidates(candidates, i, j, board[i][j])
    return candidates

def logical_solve(board, candidates):
    """Solve using only Naked Singles + record every step with hint"""
    steps = []
    while True:
        found = False
        # Naked Single search (one at a time for nice step-by-step video)
        for i in range(9):
            for j in range(9):
                if board[i][j] == 0 and len(candidates[i][j]) == 1:
                    num = next(iter(candidates[i][j]))
                    hint = f"Naked Single Hint ✨ Cell ({i+1},{j+1}) can ONLY be {num}"
                    steps.append((i, j, num, hint))
                    board[i][j] = num
                    update_candidates(candidates, i, j, num)
                    found = True
                    break
            if found:
                break
        if not found:
            break
    return steps

def generate_puzzle():
    """Generate a random puzzle that can be fully solved with Naked Singles only"""
    attempts = 0
    while attempts < 100:  # safety limit
        attempts += 1
        board = [[0] * 9 for _ in range(9)]
        solve(board)  # full solved board
        puzzle = [row[:] for row in board]

        # Remove numbers
        positions = list(range(81))
        random.shuffle(positions)
        for k in range(REMOVE_COUNT):
            pos = positions[k]
            r, c = divmod(pos, 9)
            puzzle[r][c] = 0

        # Test if Naked Singles can solve it completely
        test_board = [row[:] for row in puzzle]
        test_cands = initialize_candidates(test_board)
        logical_solve(test_board, test_cands)

        if all(all(cell != 0 for cell in row) for row in test_board):
            print(f"✅ Puzzle ready! (Clues: {81 - REMOVE_COUNT}, generated in {attempts} tries)")
            return puzzle
    raise ValueError("Could not find suitable puzzle - try lowering REMOVE_COUNT")

# ====================== MATPLOTLIB DRAWING ======================
def draw_board(ax, board, original_puzzle, highlight=None, hint_text=""):
    ax.clear()
    ax.set_xlim(0, 9)
    ax.set_ylim(0, 9)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_title(hint_text, fontsize=14, pad=25, fontweight="bold", color="#2c3e50")

    # Grid lines (thick every 3)
    for i in range(10):
        lw = 4 if i % 3 == 0 else 1.5
        ax.axhline(i, color="black", linewidth=lw)
        ax.axvline(i, color="black", linewidth=lw)

    # Numbers
    for r in range(9):
        for c in range(9):
            val = board[r][c]
            if val != 0:
                is_given = original_puzzle[r][c] != 0
                color = "#34495e" if is_given else "#e74c3c"   # gray given, red solved
                size = 26 if is_given else 28
                weight = "normal" if is_given else "bold"
                ax.text(c + 0.5, 8.5 - r, str(val),
                        ha="center", va="center", fontsize=size,
                        color=color, fontweight=weight)

    # Highlight cell being solved
    if highlight:
        hr, hc = highlight
        rect = Rectangle((hc, 8 - hr), 1, 1,
                         linewidth=5, edgecolor="#f39c12",
                         facecolor="#f1c40f", alpha=0.25)
        ax.add_patch(rect)

# ====================== BUILD ANIMATION STATES ======================
def build_animation_states(puzzle, steps):
    original_puzzle = [row[:] for row in puzzle]
    current_board = [row[:] for row in puzzle]

    states = []
    # Initial frame
    states.append({
        "board": [row[:] for row in current_board],
        "highlight": None,
        "hint": "🎥 New Sudoku Puzzle - Watch it solve itself with hints!"
    })

    for r, c, num, hint in steps:
        # Highlight + hint frame (before placing)
        states.append({
            "board": [row[:] for row in current_board],
            "highlight": (r, c),
            "hint": hint
        })
        # Place the number
        current_board[r][c] = num
        # Placed frame
        states.append({
            "board": [row[:] for row in current_board],
            "highlight": None,
            "hint": f"✅ Placed {num} at ({r+1}, {c+1})"
        })

    # Final victory frame (longer pause)
    states.append({
        "board": [row[:] for row in current_board],
        "highlight": None,
        "hint": "🎉 SOLVED! Another perfect Sudoku video ready for your spree!"
    })
    return states, original_puzzle

# ====================== ANIMATION FUNCTION ======================
def animate(frame, states, ax, original_puzzle):
    state_idx = min(frame // FRAMES_PER_STATE, len(states) - 1)
    state = states[state_idx]
    draw_board(ax, state["board"], original_puzzle, state["highlight"], state["hint"])

# ====================== MAIN ======================
if __name__ == "__main__":
    print("🚀 Starting Sudoku video creation spree...")

    # Generate puzzle + solving steps
    puzzle = generate_puzzle()
    board_for_solve = [row[:] for row in puzzle]
    candidates = initialize_candidates(board_for_solve)
    steps = logical_solve(board_for_solve, candidates)

    print(f"📝 {len(steps)} solving steps recorded with hints!")

    # Build states for animation
    states, original_puzzle = build_animation_states(puzzle, steps)

    # Create animation
    fig, ax = plt.subplots(figsize=(9, 9), facecolor="white")
    total_frames = len(states) * FRAMES_PER_STATE + 30  # extra for final pause

    ani = FuncAnimation(
        fig, animate, frames=total_frames,
        fargs=(states, ax, original_puzzle),
        interval=1000 // FPS, repeat=False, blit=False
    )

    # Save raw animation
    print("🎞️  Rendering video (this takes 10-40 seconds)...")
    writer = FFMpegWriter(fps=FPS, metadata=dict(artist="Grok Sudoku Spree"), bitrate=2500)
    raw_video = "sudoku_solving_raw.mp4"
    ani.save(raw_video, writer=writer)
    plt.close()

    # Add your background music
    print("🎵 Adding your background music...")
    video_clip = VideoFileClip(raw_video)
    if not os.path.exists(MUSIC_FILE):
        print(f"⚠️  Music file '{MUSIC_FILE}' not found! Video will be silent.")
        final_video = "sudoku_solving_video.mp4"
        video_clip.write_videofile(final_video, codec="libx264", audio_codec="aac", threads=4)
    else:
        audio_clip = AudioFileClip(MUSIC_FILE)
        # Loop or trim music to match video length
        if audio_clip.duration < video_clip.duration:
            audio_clip = audio_clip.loop(duration=video_clip.duration)
        else:
            audio_clip = audio_clip.subclip(0, video_clip.duration)

        final_clip = video_clip.set_audio(audio_clip)
        final_video = "sudoku_solving_with_music.mp4"
        final_clip.write_videofile(final_video, codec="libx264", audio_codec="aac", threads=4)
        audio_clip.close()

    video_clip.close()

    print("\n✅ DONE!")
    print(f"   Raw animation: {raw_video}")
    print(f"   Final video with your music: {final_video}")
    print("   Drop it on YouTube, TikTok, Shorts, Reels — go on your spree! 🔥")
    print("\nRun the script again for a completely new puzzle + video!")