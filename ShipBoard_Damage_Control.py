import sys
import networkx as nx
import random
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QLabel, QComboBox,
                             QGraphicsView, QGraphicsScene, QGraphicsEllipseItem,
                             QGraphicsLineItem, QGraphicsTextItem, QMessageBox, QGroupBox)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QPointF
from PyQt5.QtGui import QBrush, QPen, QColor, QFont, QPainter

# --- Configuration ---
NODE_RADIUS = 30
SPREAD_INTERVAL = 2000  # ms (Fire spreads every 2 seconds for demo speed)

# Colors
C_SAFE = QColor("#2E7D32")  # Green
C_FIRE = QColor("#D32F2F")  # Red
C_FLOOD = QColor("#1976D2")  # Blue
C_PATH = QColor("#FFD700")  # Gold (Route)
C_WALL = QColor("#555")  # Closed Door
C_OPEN = QColor("#AAA")  # Open Door


class ShipGraph:
    """
    The Logic Core using NetworkX.
    Manages the state of compartments and doors.
    """

    def __init__(self):
        self.G = nx.Graph()
        self.define_ship_layout()

    def define_ship_layout(self):
        # 1. Add Compartments (Nodes) with positions (x, y)
        # Layout: Bow (Left) to Stern (Right)

        # Bow Section
        self.add_room("BRIDGE", 100, 200)
        self.add_room("FCS", 100, 300)  # Fire Control

        # Midship
        self.add_room("CORRIDOR_FWD", 250, 250)
        self.add_room("MESS_HALL", 350, 150)
        self.add_room("GALLEY", 350, 350)
        self.add_room("MED_BAY", 450, 150)
        self.add_room("CIC", 450, 350)  # Combat Info Center
        self.add_room("CORRIDOR_AFT", 550, 250)

        # Stern Section
        self.add_room("ENGINE_ROOM", 700, 250)
        self.add_room("GENERATOR", 700, 350)
        self.add_room("STEERING", 800, 250)

        # 2. Add Connections (Hatches/Doors)
        # (u, v, is_open)
        connections = [
            ("BRIDGE", "CORRIDOR_FWD"), ("FCS", "CORRIDOR_FWD"),
            ("CORRIDOR_FWD", "MESS_HALL"), ("CORRIDOR_FWD", "GALLEY"),
            ("MESS_HALL", "MED_BAY"), ("GALLEY", "CIC"),
            ("MED_BAY", "CORRIDOR_AFT"), ("CIC", "CORRIDOR_AFT"),
            ("CORRIDOR_AFT", "ENGINE_ROOM"), ("ENGINE_ROOM", "GENERATOR"),
            ("ENGINE_ROOM", "STEERING")
        ]

        for u, v in connections:
            self.G.add_edge(u, v, open=True)

    def add_room(self, name, x, y):
        self.G.add_node(name, pos=(x, y), status="SAFE")  # Status: SAFE, FIRE, FLOOD

    def set_status(self, node, status):
        self.G.nodes[node]['status'] = status

    def toggle_door(self, u, v):
        if self.G.has_edge(u, v):
            current = self.G.edges[u, v]['open']
            self.G.edges[u, v]['open'] = not current

    def spread_hazards(self):
        """
        Simulation Step: Fire spreads to neighbors if door is OPEN.
        Flooding spreads if door is OPEN (simplified physics).
        """
        new_fires = []
        new_floods = []

        for node in self.G.nodes:
            status = self.G.nodes[node]['status']

            if status in ["FIRE", "FLOOD"]:
                # Check neighbors
                for neighbor in self.G.neighbors(node):
                    # Check door status
                    is_open = self.G.edges[node, neighbor]['open']
                    neighbor_status = self.G.nodes[neighbor]['status']

                    if is_open and neighbor_status == "SAFE":
                        if status == "FIRE":
                            new_fires.append(neighbor)
                        elif status == "FLOOD":
                            new_floods.append(neighbor)

        # Apply updates
        for n in new_fires:
            self.G.nodes[n]['status'] = "FIRE"
        for n in new_floods:
            self.G.nodes[n]['status'] = "FLOOD"

        return len(new_fires) + len(new_floods) > 0  # Return True if something changed

    def find_safe_route(self, start, end):
        """
        Calculates path avoiding FIRE/FLOOD nodes.
        Returns: List of nodes or None.
        """
        # Create a view/subgraph of only safe nodes
        safe_nodes = [n for n in self.G.nodes if self.G.nodes[n]['status'] == "SAFE"]

        # We must include start/end even if dangerous?
        # Ideally no, you can't start in a fire. But for robust logic:
        # We define "Safe Graph" as all nodes except hazardous ones.

        # Edge case: If start or end is on fire, no path.
        if self.G.nodes[start]['status'] != "SAFE" or self.G.nodes[end]['status'] != "SAFE":
            return None

        # Build subgraph
        sub = self.G.subgraph(safe_nodes)

        try:
            # Dijkstra assumes edges exist.
            # Important: Check if doors are closed?
            # In DC logic, you can open a closed door to pass,
            # UNLESS it's holding back fire.
            # For this sim, let's say you can pass closed doors (crew opens them),
            # but you simply cannot pass through a Burning Room.
            path = nx.shortest_path(sub, source=start, target=end)
            return path
        except nx.NetworkXNoPath:
            return None


# --- GUI Components ---

class SchematicScene(QGraphicsScene):
    def __init__(self, ship_graph, parent=None):
        super().__init__(parent)
        self.ship = ship_graph
        self.node_items = {}  # Map name -> QGraphicsItem
        self.edge_items = {}  # Map tuple(u,v) -> QGraphicsLineItem
        self.route_path = []  # Current highlighted path
        self.draw_graph()

    def draw_graph(self):
        self.clear()
        self.node_items = {}
        self.edge_items = {}

        # 1. Draw Edges (Doors/Hatches)
        for u, v in self.ship.G.edges:
            pos_u = self.ship.G.nodes[u]['pos']
            pos_v = self.ship.G.nodes[v]['pos']

            # Line
            line = QGraphicsLineItem(pos_u[0], pos_u[1], pos_v[0], pos_v[1])
            self.update_edge_visual(line, u, v)
            line.setZValue(0)  # Bottom layer
            self.addItem(line)
            self.edge_items[(u, v)] = line
            self.edge_items[(v, u)] = line  # Bi-directional lookup

            # Door Icon (Midpoint)
            mid_x = (pos_u[0] + pos_v[0]) / 2
            mid_y = (pos_u[1] + pos_v[1]) / 2
            door_lbl = QGraphicsTextItem("HATCH")
            door_lbl.setFont(QFont("Arial", 6))
            door_lbl.setPos(mid_x - 10, mid_y - 10)
            self.addItem(door_lbl)

        # 2. Draw Nodes (Compartments)
        for node in self.ship.G.nodes:
            pos = self.ship.G.nodes[node]['pos']
            x, y = pos

            # Circle
            ellipse = QGraphicsEllipseItem(x - NODE_RADIUS, y - NODE_RADIUS, NODE_RADIUS * 2, NODE_RADIUS * 2)
            self.update_node_visual(ellipse, node)
            ellipse.setZValue(1)

            # Store data in item for click handling
            ellipse.setData(0, node)

            self.addItem(ellipse)
            self.node_items[node] = ellipse

            # Label
            lbl = QGraphicsTextItem(node)
            lbl.setDefaultTextColor(Qt.white)
            lbl.setFont(QFont("Arial", 8, QFont.Bold))
            # Center text approx
            rect = lbl.boundingRect()
            lbl.setPos(x - rect.width() / 2, y - rect.height() / 2)
            lbl.setZValue(2)
            self.addItem(lbl)

    def update_node_visual(self, item, node_name):
        status = self.ship.G.nodes[node_name]['status']

        if status == "SAFE":
            col = C_SAFE
        elif status == "FIRE":
            col = C_FIRE
        else:
            col = C_FLOOD

        # Highlight if in calculated route
        if node_name in self.route_path:
            pen = QPen(C_PATH, 4)
        else:
            pen = QPen(Qt.black, 2)

        item.setBrush(QBrush(col))
        item.setPen(pen)

    def update_edge_visual(self, item, u, v):
        is_open = self.ship.G.edges[u, v]['open']

        # Check if this edge connects two nodes in the route path
        in_path = False
        if len(self.route_path) > 1:
            for i in range(len(self.route_path) - 1):
                if {u, v} == {self.route_path[i], self.route_path[i + 1]}:
                    in_path = True
                    break

        if in_path:
            col = C_PATH
            width = 4
        elif is_open:
            col = C_OPEN
            width = 6
        else:
            col = C_WALL
            width = 2

        pen = QPen(col, width)
        if not is_open:
            pen.setStyle(Qt.DotLine)

        item.setPen(pen)

    def refresh_visuals(self):
        for node, item in self.node_items.items():
            self.update_node_visual(item, node)

        for (u, v), item in self.edge_items.items():
            self.update_edge_visual(item, u, v)


class DamageControlApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DC-NET: Shipboard Crisis Management System")
        self.setGeometry(100, 100, 1100, 700)
        self.setStyleSheet("background-color: #222; color: #EEE;")

        self.ship = ShipGraph()

        self.selected_node = None
        self.selected_tool = "SELECT"  # SELECT, FIRE, FLOOD, DOOR, REPAIR

        self.init_ui()

        # Simulation Timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.sim_tick)
        self.timer.start(SPREAD_INTERVAL)

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)

        # --- LEFT PANEL: CONTROLS ---
        ctrl_panel = QWidget()
        ctrl_panel.setFixedWidth(250)
        ctrl_layout = QVBoxLayout(ctrl_panel)

        # Header
        lbl_h = QLabel("DAMAGE CONTROL")
        lbl_h.setStyleSheet("font-size: 18px; font-weight: bold; color: #FFF;")
        ctrl_layout.addWidget(lbl_h)

        # Toolbox
        grp_tools = QGroupBox("ACTION TOOLBOX")
        grp_tools.setStyleSheet("border: 1px solid #555; font-weight: bold;")
        t_layout = QVBoxLayout(grp_tools)

        self.btn_select = QPushButton("🔍 SELECT / INFO")
        self.btn_fire = QPushButton("🔥 SET FIRE")
        self.btn_flood = QPushButton("💧 SET FLOOD")
        self.btn_repair = QPushButton("🛠️ REPAIR / CLEAR")
        self.btn_door = QPushButton("🚪 TOGGLE HATCH")

        for btn in [self.btn_select, self.btn_fire, self.btn_flood, self.btn_repair, self.btn_door]:
            btn.setCheckable(True)
            btn.setStyleSheet("padding: 8px; text-align: left;")
            btn.clicked.connect(self.change_tool)
            t_layout.addWidget(btn)

        self.btn_select.setChecked(True)
        ctrl_layout.addWidget(grp_tools)

        # Navigation Tool
        grp_nav = QGroupBox("CREW NAVIGATION")
        grp_nav.setStyleSheet("border: 1px solid #555; font-weight: bold;")
        n_layout = QVBoxLayout(grp_nav)

        n_layout.addWidget(QLabel("Start Point:"))
        self.combo_start = QComboBox()
        self.combo_start.addItems(list(self.ship.G.nodes))
        n_layout.addWidget(self.combo_start)

        n_layout.addWidget(QLabel("Destination:"))
        self.combo_end = QComboBox()
        self.combo_end.addItems(list(self.ship.G.nodes))
        # Default interesting path
        self.combo_end.setCurrentText("ENGINE_ROOM")
        n_layout.addWidget(self.combo_end)

        btn_route = QPushButton("CALCULATE SAFE ROUTE")
        btn_route.setStyleSheet("background-color: #FBC02D; color: black; font-weight: bold; padding: 10px;")
        btn_route.clicked.connect(self.calc_route)
        n_layout.addWidget(btn_route)

        self.lbl_route_status = QLabel("ROUTE: N/A")
        self.lbl_route_status.setWordWrap(True)
        self.lbl_route_status.setStyleSheet("color: #AAA; font-size: 10px;")
        n_layout.addWidget(self.lbl_route_status)

        ctrl_layout.addWidget(grp_nav)

        ctrl_layout.addStretch()
        layout.addWidget(ctrl_panel)

        # --- RIGHT PANEL: SCHEMATIC ---
        self.scene = SchematicScene(self.ship)
        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.Antialiasing)
        self.view.setBackgroundBrush(QBrush(QColor("#1a1a1a")))

        # Override mousePressEvent for the view to handle clicks manually
        self.view.mousePressEvent = self.view_mouse_press

        layout.addWidget(self.view)

    def change_tool(self):
        sender = self.sender()
        # Uncheck others
        for btn in [self.btn_select, self.btn_fire, self.btn_flood, self.btn_repair, self.btn_door]:
            if btn != sender:
                btn.setChecked(False)

        if sender == self.btn_fire:
            self.selected_tool = "FIRE"
        elif sender == self.btn_flood:
            self.selected_tool = "FLOOD"
        elif sender == self.btn_repair:
            self.selected_tool = "REPAIR"
        elif sender == self.btn_door:
            self.selected_tool = "DOOR"
        else:
            self.selected_tool = "SELECT"

    def view_mouse_press(self, event):
        # Translate to scene coords
        pos = self.view.mapToScene(event.pos())
        item = self.scene.itemAt(pos, self.view.transform())

        if not item: return

        # Check if Node (Ellipse)
        if isinstance(item, QGraphicsEllipseItem):
            node_name = item.data(0)
            self.handle_node_click(node_name)
        # Check if Line (Edge) - Need smarter hit detection or just assume nodes control doors?
        # Let's say clicking a node in DOOR mode toggles all its doors?
        # Or simplistic: Click line. But lines are thin.
        # Let's stick to Node logic for Fire/Flood, and maybe node-neighbor logic for doors?
        # Actually, let's iterate items near click for Lines.
        elif isinstance(item, QGraphicsLineItem) and self.selected_tool == "DOOR":
            # Find which edge this is
            for (u, v), edge_item in self.scene.edge_items.items():
                if edge_item == item:
                    self.ship.toggle_door(u, v)
                    self.scene.refresh_visuals()
                    self.recalc_route_if_active()
                    break

    def handle_node_click(self, node):
        if self.selected_tool == "FIRE":
            self.ship.set_status(node, "FIRE")
        elif self.selected_tool == "FLOOD":
            self.ship.set_status(node, "FLOOD")
        elif self.selected_tool == "REPAIR":
            self.ship.set_status(node, "SAFE")
        elif self.selected_tool == "DOOR":
            # Toggle all doors connected to this room (Quick seal)
            for n in self.ship.G.neighbors(node):
                self.ship.toggle_door(node, n)

        self.scene.refresh_visuals()
        self.recalc_route_if_active()

    def sim_tick(self):
        changed = self.ship.spread_hazards()
        if changed:
            self.scene.refresh_visuals()
            self.recalc_route_if_active()

    def calc_route(self):
        start = self.combo_start.currentText()
        end = self.combo_end.currentText()

        if start == end:
            self.lbl_route_status.setText("Start and End are same.")
            return

        path = self.ship.find_safe_route(start, end)

        if path:
            self.scene.route_path = path
            path_str = " -> ".join(path)
            self.lbl_route_status.setText(f"PATH FOUND:\n{path_str}")
            self.lbl_route_status.setStyleSheet("color: #4CAF50; font-size: 10px;")
        else:
            self.scene.route_path = []
            self.lbl_route_status.setText("CRITICAL: NO SAFE ROUTE AVAILABLE.\nCompartments blocked by Hazard.")
            self.lbl_route_status.setStyleSheet("color: #F44336; font-size: 10px; font-weight: bold;")

        self.scene.refresh_visuals()

    def recalc_route_if_active(self):
        # If a route is currently displayed, re-check it dynamically
        if self.scene.route_path:
            self.calc_route()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DamageControlApp()
    window.show()
    sys.exit(app.exec_())