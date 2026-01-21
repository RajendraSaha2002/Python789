from typing import List, Tuple
from colorama import Fore, Style, init as colorama_init

# Initialize colorama for cross-platform color output
colorama_init(autoreset=True)

Cell = str
Maze = List[List[Cell]]
Point = Tuple[int, int]


def get_start_finish(Maza: Maze) -> Tuple[Point, Point]:
    """
    Find the start on the top row (first 'c') and finish on the bottom row (first 'c').
    """
    cols = len(Maza[0])
    start_candidates = [i for i in range(cols) if Maza[0][i] == 'c']
    finish_candidates = [i for i in range(cols) if Maza[-1][i] == 'c']
    if not start_candidates or not finish_candidates:
        raise ValueError("Start or finish not found (need 'c' on top and bottom rows).")
    return (0, start_candidates[0]), (len(Maza) - 1, finish_candidates[0])


def print_maze(Maza: Maze) -> None:
    """
    Pretty-print the maze with colors:
    - 'w' walls in red
    - 'c' clear cells in green
    - 'p' path in blue
    - 'u' unknown in white
    """
    color_map = {
        'w': Fore.RED,
        'c': Fore.GREEN,
        'p': Fore.BLUE,
        'u': Fore.WHITE,
    }
    for row in Maza:
        for cell in row:
            color = color_map.get(cell, Fore.WHITE)
            # Print the cell character colored, then reset automatically via autoreset=True
            print(f"{color}{cell}{Style.RESET_ALL}", end=" ")
        print()  # newline


def solve_maze(Maza: Maze, Start: Point, Finish: Point) -> List[Point]:
    """
    Depth-first search with backtracking. Marks the successful path cells as 'p'.
    Returns the list of points forming the path from start to finish (inclusive).
    """
    rows, cols = len(Maza), len(Maza[0])
    Path: List[Point] = []

    def in_bounds(r: int, c: int) -> bool:
        return 0 <= r < rows and 0 <= c < cols

    def dfs(r: int, c: int) -> bool:
        # If we reached the finish, record and stop.
        Path.append((r, c))
        if (r, c) == Finish:
            return True

        # Mark current as part of path
        Maza[r][c] = 'p'

        # Explore in order: down, right, up, left
        for dr, dc in ((1, 0), (0, 1), (-1, 0), (0, -1)):
            nr, nc = r + dr, c + dc
            if in_bounds(nr, nc) and Maza[nr][nc] == 'c':
                if dfs(nr, nc):
                    return True

        # Backtrack: unmark and remove from path
        Maza[r][c] = 'c'
        Path.pop()
        return False

    # Ensure start cell is considered traversable
    sr, sc = Start
    if Maza[sr][sc] == 'c':
        Maza[sr][sc] = 'p'  # mark start visually; dfs will handle correctly

    # Start DFS from start (but pass through as if it were 'c')
    # Temporarily set start back to 'c' so dfs can mark 'p' only on the successful path
    Maza[sr][sc] = 'c'
    found = dfs(sr, sc)
    if not found:
        raise RuntimeError("No path found from start to finish.")

    # Ensure the final path cells remain marked as 'p'
    for r, c in Path:
        Maza[r][c] = 'p'

    return Path


if __name__ == "__main__":
    maze: Maze = [
        ['w', 'c', 'w', 'w', 'w', 'w', 'w', 'w', 'w', 'w', 'w', 'w', 'w', 'w', 'w', 'w', 'w', 'w', 'w', 'w', 'w', 'w', 'w', 'w', 'w', 'w', 'w'],
        ['w', 'c', 'c', 'w', 'c', 'w', 'c', 'c', 'w', 'w', 'c', 'c', 'c', 'c', 'c', 'w', 'w', 'c', 'w', 'w', 'c', 'c', 'c', 'c', 'c', 'c', 'w'],
        ['w', 'w', 'c', 'w', 'c', 'c', 'c', 'w', 'w', 'w', 'w', 'w', 'w', 'w', 'c', 'c', 'c', 'c', 'c', 'w', 'w', 'w', 'w', 'w', 'w', 'c', 'w'],
        ['w', 'c', 'c', 'c', 'c', 'w', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'w', 'c', 'w', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'w'],
        ['w', 'w', 'w', 'c', 'w', 'w', 'c', 'w', 'c', 'w', 'c', 'w', 'w', 'w', 'w', 'w', 'w', 'w', 'w', 'w', 'w', 'c', 'w', 'w', 'w', 'c', 'w'],
        ['w', 'c', 'c', 'c', 'c', 'w', 'w', 'w', 'w', 'w', 'w', 'w', 'w', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'w', 'c', 'c', 'c', 'w'],
        ['w', 'c', 'w', 'c', 'w', 'w', 'w', 'w', 'c', 'c', 'w', 'c', 'w', 'w', 'w', 'c', 'w', 'w', 'w', 'w', 'w', 'w', 'w', 'w', 'w', 'c', 'w'],
        ['w', 'w', 'w', 'w', 'w', 'w', 'c', 'w', 'w', 'c', 'c', 'c', 'w', 'c', 'w', 'w', 'w', 'w', 'w', 'w', 'c', 'c', 'c', 'c', 'c', 'c', 'w'],
        ['w', 'c', 'c', 'c', 'c', 'c', 'c', 'w', 'w', 'w', 'w', 'c', 'w', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'w', 'c', 'w', 'c', 'w', 'w'],
        ['w', 'w', 'c', 'w', 'c', 'w', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'w', 'w', 'c', 'w', 'c', 'w', 'c', 'w', 'c', 'w', 'c', 'c', 'w'],
        ['w', 'w', 'w', 'w', 'w', 'w', 'w', 'w', 'w', 'w', 'w', 'w', 'w', 'w', 'w', 'w', 'w', 'w', 'w', 'w', 'w', 'w', 'w', 'w', 'w', 'c', 'w'],
    ]

    start, finish = get_start_finish(maze)
    path = solve_maze(maze, start, finish)

    print("Solved path length:", len(path))
    print_maze(maze)