import pygame
import heapq
import sys

# --- Configuration ---
TILE_SIZE = 60
GRID_W, GRID_H = 15, 10
WIDTH = GRID_W * TILE_SIZE + 250  # Extra space for UI
HEIGHT = GRID_H * TILE_SIZE
FPS = 30

# Colors
COL_OPEN = (200, 230, 200)  # Light Green
COL_FOREST = (34, 139, 34)  # Dark Green
COL_URBAN = (100, 100, 100)  # Grey
COL_ROAD = (240, 230, 140)  # Khaki
COL_MOUNTAIN = (80, 50, 30)  # Brown
COL_GRID = (50, 50, 50)
COL_PATH = (0, 0, 255)  # Blue Line
COL_KILLZONE = (255, 0, 0, 100)  # Transparent Red
COL_UI_BG = (30, 30, 40)
COL_TEXT = (255, 255, 255)

# Danger Costs (The "Weight" for pathfinding)
COSTS = {
    "OPEN": 1,
    "ROAD": 1,
    "FOREST": 8,  # High danger
    "URBAN": 20,  # Extreme danger
    "MOUNTAIN": 999  # Impassable
}


# --- Logic Engine ---

class Tile:
    def __init__(self, x, y, type_key="OPEN"):
        self.x = x
        self.y = y
        self.type = type_key
        self.rect = pygame.Rect(x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE)

    def draw(self, screen, font):
        # Base Color
        c = COL_OPEN
        label = ""
        if self.type == "FOREST":
            c = COL_FOREST; label = "🌲"
        elif self.type == "URBAN":
            c = COL_URBAN; label = "🏢"
        elif self.type == "ROAD":
            c = COL_ROAD; label = "🛣️"
        elif self.type == "MOUNTAIN":
            c = COL_MOUNTAIN; label = "⛰️"

        pygame.draw.rect(screen, c, self.rect)
        pygame.draw.rect(screen, COL_GRID, self.rect, 1)  # Grid line

        # Simple Icon
        if label:
            # Pygame doesn't render colored emojis well by default font,
            # so we use text representation or simple shapes if needed.
            # Using basic text for simplicity.
            txt = font.render(label, True, (0, 0, 0))
            screen.blit(txt, (self.rect.centerx - txt.get_width() // 2, self.rect.centery - txt.get_height() // 2))


class Pathfinder:
    def __init__(self, grid):
        self.grid = grid
        self.width = len(grid)
        self.height = len(grid[0])

    def get_neighbors(self, node):
        x, y = node
        candidates = [
            (x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)
        ]
        valid = []
        for nx, ny in candidates:
            if 0 <= nx < self.width and 0 <= ny < self.height:
                if self.grid[nx][ny].type != "MOUNTAIN":
                    valid.append((nx, ny))
        return valid

    def find_safest_path(self, start, end):
        # A* Algorithm minimizing Danger Cost
        # Priority Queue: (cost, current_node)
        frontier = []
        heapq.heappush(frontier, (0, start))

        came_from = {}
        cost_so_far = {}
        came_from[start] = None
        cost_so_far[start] = 0

        while frontier:
            current_cost, current = heapq.heappop(frontier)

            if current == end:
                break

            for next_node in self.get_neighbors(current):
                # Calculate new cost
                tile_type = self.grid[next_node[0]][next_node[1]].type
                new_cost = cost_so_far[current] + COSTS[tile_type]

                if next_node not in cost_so_far or new_cost < cost_so_far[next_node]:
                    cost_so_far[next_node] = new_cost
                    priority = new_cost + self.heuristic(end, next_node)
                    heapq.heappush(frontier, (priority, next_node))
                    came_from[next_node] = current

        return self.reconstruct_path(came_from, start, end)

    def heuristic(self, a, b):
        # Manhattan distance
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    def reconstruct_path(self, came_from, start, end):
        if end not in came_from:
            return []  # No path found

        current = end
        path = []
        while current != start:
            path.append(current)
            current = came_from[current]
        path.append(start)
        path.reverse()
        return path


# --- GUI Application ---

class MapEditor:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Ambush Zone Terrain Analyzer")
        self.clock = pygame.time.Clock()
        # Fallback font handling
        try:
            self.font = pygame.font.SysFont("Segoe UI Emoji", 24)
        except:
            self.font = pygame.font.SysFont("Arial", 24)

        self.ui_font = pygame.font.SysFont("Consolas", 16)

        # Init Grid
        self.grid = [[Tile(x, y) for y in range(GRID_H)] for x in range(GRID_W)]
        self.pathfinder = Pathfinder(self.grid)

        # State
        self.selected_tool = "FOREST"
        self.start_pos = None
        self.end_pos = None
        self.current_path = []
        self.kill_zones = []  # List of rects to highlight

        # Setup UI Buttons
        self.buttons = []
        tools = ["OPEN", "FOREST", "URBAN", "ROAD", "MOUNTAIN", "SET START", "SET END", "INSPECT"]
        for i, t in enumerate(tools):
            rect = pygame.Rect(GRID_W * TILE_SIZE + 20, 50 + i * 50, 200, 40)
            self.buttons.append({"label": t, "rect": rect})

    def handle_click(self, pos):
        mx, my = pos

        # 1. Check UI Buttons
        for btn in self.buttons:
            if btn["rect"].collidepoint(mx, my):
                self.selected_tool = btn["label"]
                self.kill_zones = []  # Clear inspection
                return

        # 2. Check Grid Click
        gx = mx // TILE_SIZE
        gy = my // TILE_SIZE

        if 0 <= gx < GRID_W and 0 <= gy < GRID_H:
            if self.selected_tool == "SET START":
                self.start_pos = (gx, gy)
                self.recalc_path()
            elif self.selected_tool == "SET END":
                self.end_pos = (gx, gy)
                self.recalc_path()
            elif self.selected_tool == "INSPECT":
                self.calc_kill_zone(gx, gy)
            else:
                # Painting Terrain
                self.grid[gx][gy].type = self.selected_tool
                # Reset start/end if overwritten by mountain
                if self.selected_tool == "MOUNTAIN":
                    if self.start_pos == (gx, gy): self.start_pos = None
                    if self.end_pos == (gx, gy): self.end_pos = None
                self.recalc_path()

    def calc_kill_zone(self, gx, gy):
        """Highligts adjacent tiles if clicked tile is an ambush spot."""
        tile_type = self.grid[gx][gy].type
        self.kill_zones = []

        if tile_type in ["FOREST", "URBAN", "MOUNTAIN"]:
            # Logic: Enemy in Forest/Urban can shoot at neighbors
            # Radius 1 block (3x3 grid)
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    nx, ny = gx + dx, gy + dy
                    if 0 <= nx < GRID_W and 0 <= ny < GRID_H:
                        if (nx, ny) != (gx, gy):  # Don't highlight self
                            # Calculate screen rect
                            r = pygame.Rect(nx * TILE_SIZE, ny * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                            self.kill_zones.append(r)
        else:
            print("Selected tile provides no cover for ambush.")

    def recalc_path(self):
        if self.start_pos and self.end_pos:
            self.current_path = self.pathfinder.find_safest_path(self.start_pos, self.end_pos)
        else:
            self.current_path = []

    def draw_ui(self):
        # UI Panel Background
        ui_rect = pygame.Rect(GRID_W * TILE_SIZE, 0, 250, HEIGHT)
        pygame.draw.rect(self.screen, COL_UI_BG, ui_rect)

        # Header
        head = self.ui_font.render("TACTICAL MAP EDITOR", True, (0, 255, 255))
        self.screen.blit(head, (GRID_W * TILE_SIZE + 20, 20))

        # Buttons
        for btn in self.buttons:
            # Highlight selected
            col = (100, 100, 100)
            if self.selected_tool == btn["label"]:
                col = (0, 200, 0)

            pygame.draw.rect(self.screen, col, btn["rect"], border_radius=5)
            pygame.draw.rect(self.screen, (200, 200, 200), btn["rect"], 2, border_radius=5)

            lbl = self.ui_font.render(btn["label"], True, COL_TEXT)
            self.screen.blit(lbl, (btn["rect"].x + 10, btn["rect"].y + 10))

        # Stats
        if self.start_pos and self.end_pos:
            status_y = HEIGHT - 100
            s_txt = self.ui_font.render(f"PATH LENGTH: {len(self.current_path)}", True, COL_TEXT)
            self.screen.blit(s_txt, (GRID_W * TILE_SIZE + 20, status_y))

            # Calc Total Danger Score
            danger = sum([COSTS[self.grid[x][y].type] for x, y in self.current_path])
            d_col = (0, 255, 0) if danger < 20 else (255, 0, 0)
            d_txt = self.ui_font.render(f"DANGER SCORE: {danger}", True, d_col)
            self.screen.blit(d_txt, (GRID_W * TILE_SIZE + 20, status_y + 25))

    def draw_overlays(self):
        # 1. Kill Zones
        if self.kill_zones:
            s = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            for r in self.kill_zones:
                pygame.draw.rect(s, COL_KILLZONE, r)
                # Draw crosshairs
                pygame.draw.line(s, (255, 0, 0), r.topleft, r.bottomright, 2)
                pygame.draw.line(s, (255, 0, 0), r.topright, r.bottomleft, 2)
            self.screen.blit(s, (0, 0))

        # 2. Path
        if len(self.current_path) > 1:
            # Convert grid coords to pixel centers
            points = [(p[0] * TILE_SIZE + TILE_SIZE // 2, p[1] * TILE_SIZE + TILE_SIZE // 2) for p in self.current_path]
            pygame.draw.lines(self.screen, COL_PATH, False, points, 5)

        # 3. Start/End Markers
        if self.start_pos:
            sx, sy = self.start_pos
            pygame.draw.circle(self.screen, (0, 0, 255),
                               (sx * TILE_SIZE + TILE_SIZE // 2, sy * TILE_SIZE + TILE_SIZE // 2), 15)
            # Label
            st = self.ui_font.render("S", True, (255, 255, 255))
            self.screen.blit(st, (sx * TILE_SIZE + TILE_SIZE // 2 - 5, sy * TILE_SIZE + TILE_SIZE // 2 - 8))

        if self.end_pos:
            ex, ey = self.end_pos
            pygame.draw.circle(self.screen, (0, 255, 0),
                               (ex * TILE_SIZE + TILE_SIZE // 2, ey * TILE_SIZE + TILE_SIZE // 2), 15)
            et = self.ui_font.render("E", True, (0, 0, 0))
            self.screen.blit(et, (ex * TILE_SIZE + TILE_SIZE // 2 - 5, ey * TILE_SIZE + TILE_SIZE // 2 - 8))

    def run(self):
        running = True
        while running:
            # Events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:  # Left Click
                        self.handle_click(pygame.mouse.get_pos())
                elif event.type == pygame.MOUSEMOTION:
                    if pygame.mouse.get_pressed()[0]:  # Drag to paint
                        # Only paint if tool is terrain
                        if self.selected_tool not in ["SET START", "SET END", "INSPECT"]:
                            self.handle_click(pygame.mouse.get_pos())

            # Draw
            self.screen.fill((0, 0, 0))

            # Grid Tiles
            for row in self.grid:
                for tile in row:
                    tile.draw(self.screen, self.font)

            self.draw_overlays()
            self.draw_ui()

            pygame.display.flip()
            self.clock.tick(FPS)

        pygame.quit()


if __name__ == "__main__":
    editor = MapEditor()
    editor.run()