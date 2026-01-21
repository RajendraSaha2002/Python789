import sys
import networkx as nx
import random
import math
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QLabel, QFrame,
                             QGroupBox, QGridLayout, QProgressBar, QMessageBox)
from PyQt5.QtCore import Qt, QTimer, QPointF
from PyQt5.QtGui import QPainter, QPen, QColor, QBrush, QFont, QRadialGradient

# --- Configuration ---
WIDTH, HEIGHT = 1100, 700
TICK_RATE = 1000  # ms (1 second per infection step)

# Colors
C_BG = QColor("#101015")
C_NODE_CLEAN = QColor("#00E676")  # Bright Green
C_NODE_INFECTED = QColor("#FF1744")  # Red
C_NODE_ISOLATED = QColor("#607D8B")  # Grey
C_EDGE_ACTIVE = QColor("#00E676")
C_EDGE_INFECTED = QColor("#FF1744")
C_EDGE_CUT = QColor("#333333")


class NetworkCore:
    """
    The Logic Engine using NetworkX.
    Manages the topology and infection state.
    """

    def __init__(self):
        self.G = nx.Graph()
        self.sectors = {}  # {id: {'name': str, 'pos': (x,y), 'state': status}}
        self.build_network()

        # Infection State
        self.patient_zero = "GLOBAL_NET"
        self.sectors[self.patient_zero]['state'] = "INFECTED"

        self.game_over = False

    def build_network(self):
        # Define Nodes
        # Central Hubs
        self.add_sector("GLOBAL_NET", 100, 350, "Global Internet Uplink")
        self.add_sector("NATIONAL_GATEWAY", 300, 350, "National ISP Backbone")

        # Critical Sectors (Leafs)
        self.add_sector("ENERGY", 600, 150, "Power Grid / Nuclear")
        self.add_sector("BANKING", 600, 250, "Financial Exchange")
        self.add_sector("MILITARY", 600, 350, "Defense Network (MILNET)")
        self.add_sector("HEALTH", 600, 450, "Hospital Systems")
        self.add_sector("TRANSPORT", 600, 550, "Air Traffic / Rail")

        # Define Connections (The Pipes)
        self.add_connection("GLOBAL_NET", "NATIONAL_GATEWAY")
        self.add_connection("NATIONAL_GATEWAY", "ENERGY")
        self.add_connection("NATIONAL_GATEWAY", "BANKING")
        self.add_connection("NATIONAL_GATEWAY", "MILITARY")
        self.add_connection("NATIONAL_GATEWAY", "HEALTH")
        self.add_connection("NATIONAL_GATEWAY", "TRANSPORT")

        # Inter-sector connectivity (Risk factors)
        # e.g., Banking talks to Transport
        self.add_connection("BANKING", "TRANSPORT")
        self.add_connection("ENERGY", "MILITARY")

    def add_sector(self, s_id, x, y, name):
        self.G.add_node(s_id)
        self.sectors[s_id] = {
            'name': name,
            'pos': (x, y),
            'state': 'CLEAN',  # CLEAN, INFECTED, ISOLATED
            'original_edges': []  # Store connections for reconnection (optional)
        }

    def add_connection(self, u, v):
        self.G.add_edge(u, v, active=True)

    def toggle_isolation(self, s_id):
        """
        The Kill Switch Logic.
        Disconnects a node from the graph logic completely.
        """
        current = self.sectors[s_id]['state']

        if current == 'ISOLATED':
            # Reconnect Logic (Not usually recommended during attack, but allowed)
            # Simplification: If we reconnect, we assume we restore to CLEAN unless
            # neighbors are infected, in which case it risks reinfection next tick.
            # Ideally, restore state to what it was or CLEAN if scrubbed.
            # Here: We just set state to CLEAN and let infection logic take over.
            self.sectors[s_id]['state'] = 'CLEAN'
            # Edges are logically "active" again by virtue of state check

        else:
            # DISCONNECT
            self.sectors[s_id]['state'] = 'ISOLATED'

    def propagate_virus(self):
        """
        Spreads infection from Infected nodes to connected, non-isolated neighbors.
        """
        if self.game_over: return

        # Snapshot current state to avoid cascading instant infection
        current_infected = [n for n in self.G.nodes if self.sectors[n]['state'] == 'INFECTED']

        for node in current_infected:
            # If the source node got isolated, it can't spread
            if self.sectors[node]['state'] == 'ISOLATED':
                continue

            # Find neighbors
            neighbors = self.G.neighbors(node)
            for neighbor in neighbors:
                # Check link status
                # Link is valid only if BOTH nodes are NOT isolated
                if self.sectors[neighbor]['state'] != 'ISOLATED':

                    # Infection Probability (Simulate Firewall struggle)
                    # Military is harder to hack than Transport
                    resistance = 0.3 if neighbor == "MILITARY" else 0.8

                    if self.sectors[neighbor]['state'] == 'CLEAN':
                        if random.random() < resistance:
                            self.sectors[neighbor]['state'] = 'INFECTED'

    def get_stats(self):
        total = len(self.sectors)
        infected = len([n for n in self.sectors if self.sectors[n]['state'] == 'INFECTED'])
        isolated = len([n for n in self.sectors if self.sectors[n]['state'] == 'ISOLATED'])
        clean = total - infected - isolated
        return clean, infected, isolated


# --- GUI: Network Visualizer ---

class NetworkMap(QWidget):
    def __init__(self, core):
        super().__init__()
        self.core = core
        self.setMinimumWidth(750)
        self.setStyleSheet("background-color: #101015; border-right: 2px solid #333;")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 1. Draw Edges (Pipes)
        # Iterate all edges in graph
        for u, v in self.core.G.edges:
            u_data = self.core.sectors[u]
            v_data = self.core.sectors[v]

            p1 = QPointF(*u_data['pos'])
            p2 = QPointF(*v_data['pos'])

            # Logic: Determine line color
            # If either node is ISOLATED, the line is "Cut" (Grey/Dotted)
            # If source is INFECTED and dest is CLEAN, line is "Danger" (Red gradient?)
            # If both CLEAN, Green.

            u_state = u_data['state']
            v_state = v_data['state']

            if u_state == 'ISOLATED' or v_state == 'ISOLATED':
                pen = QPen(C_EDGE_CUT, 2, Qt.DotLine)
            elif u_state == 'INFECTED' or v_state == 'INFECTED':
                pen = QPen(C_EDGE_INFECTED, 3)
            else:
                pen = QPen(C_EDGE_ACTIVE, 3)

            painter.setPen(pen)
            painter.drawLine(p1, p2)

        # 2. Draw Nodes
        for s_id, data in self.core.sectors.items():
            x, y = data['pos']
            state = data['state']
            name = data['name']

            if state == 'CLEAN':
                col = C_NODE_CLEAN
                glow = QColor(0, 230, 118, 50)
            elif state == 'INFECTED':
                col = C_NODE_INFECTED
                glow = QColor(255, 23, 68, 50)
            else:
                col = C_NODE_ISOLATED
                glow = Qt.transparent

            # Draw Glow
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(glow))
            painter.drawEllipse(QPointF(x, y), 40, 40)

            # Draw Core
            painter.setBrush(QBrush(col))
            painter.drawEllipse(QPointF(x, y), 15, 15)

            # Draw Label
            painter.setPen(QColor("white"))
            painter.setFont(QFont("Consolas", 10, QFont.Bold))
            painter.drawText(int(x - 40), int(y + 35), s_id)

            painter.setFont(QFont("Arial", 8))
            painter.setPen(QColor("#AAA"))
            painter.drawText(int(x - 40), int(y + 50), name)


# --- GUI: Main Console ---

class KillSwitchApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NATIONAL CYBER DEFENSE: NETWORK SEGMENTATION CONSOLE")
        self.setGeometry(100, 100, WIDTH, HEIGHT)
        self.setStyleSheet("""
            QMainWindow { background-color: #101015; }
            QLabel { color: #EEE; font-family: Consolas; }
            QGroupBox { border: 1px solid #444; margin-top: 10px; font-weight: bold; color: #AAA; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px; }
        """)

        self.core = NetworkCore()

        self.init_ui()

        # Simulation Loop
        self.timer = QTimer()
        self.timer.timeout.connect(self.game_tick)
        self.timer.start(TICK_RATE)

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)

        # --- LEFT: MAP ---
        self.map_view = NetworkMap(self.core)
        layout.addWidget(self.map_view)

        # --- RIGHT: CONTROL PANEL ---
        controls = QWidget()
        controls.setFixedWidth(300)
        c_layout = QVBoxLayout(controls)

        # Header
        lbl_head = QLabel("INFRASTRUCTURE\nPROTECTION")
        lbl_head.setStyleSheet(
            "font-size: 24px; font-weight: bold; color: #FFF; padding: 10px; border-bottom: 2px solid #555;")
        lbl_head.setAlignment(Qt.AlignCenter)
        c_layout.addWidget(lbl_head)

        # Stats
        self.lbl_stats = QLabel("STATUS: MONITORING")
        self.lbl_stats.setStyleSheet("font-size: 14px; margin-top: 10px;")
        c_layout.addWidget(self.lbl_stats)

        # Switches
        grp_switches = QGroupBox("ISOLATION CONTROLS (KILL SWITCHES)")
        sw_layout = QVBoxLayout(grp_switches)
        sw_layout.setSpacing(10)

        # Create a button for each sector (except Global)
        self.buttons = {}
        target_sectors = ["NATIONAL_GATEWAY", "ENERGY", "BANKING", "MILITARY", "HEALTH", "TRANSPORT"]

        for s_id in target_sectors:
            btn = QPushButton(f"ISOLATE: {s_id}")
            btn.setCheckable(True)
            btn.setFixedHeight(40)
            btn.setStyleSheet(self.get_btn_style(False))
            btn.clicked.connect(lambda checked, s=s_id: self.toggle_sector(s, checked))
            sw_layout.addWidget(btn)
            self.buttons[s_id] = btn

        c_layout.addWidget(grp_switches)

        # Master Switch
        btn_master = QPushButton("⚠️ SEVER GLOBAL UPLINK ⚠️")
        btn_master.setFixedHeight(60)
        btn_master.setStyleSheet("""
            QPushButton {
                background-color: #B71C1C; color: white; font-weight: bold; font-size: 14px;
                border: 2px solid #FF5252; border-radius: 5px;
            }
            QPushButton:hover { background-color: #FF0000; }
        """)
        btn_master.clicked.connect(self.sever_global)
        c_layout.addWidget(btn_master)

        # Legend
        grp_leg = QGroupBox("LEGEND")
        leg_lyt = QVBoxLayout(grp_leg)
        leg_lyt.addWidget(QLabel("🟢 CLEAN: Secure Operation"))
        leg_lyt.addWidget(QLabel("🔴 INFECTED: Malware Present"))
        leg_lyt.addWidget(QLabel("⚪ ISOLATED: Air-Gapped"))
        c_layout.addWidget(grp_leg)

        c_layout.addStretch()
        layout.addWidget(controls)

    def get_btn_style(self, isolated):
        if isolated:
            return """
                QPushButton {
                    background-color: #DDD; color: #333; font-weight: bold;
                    border: 2px solid #FFF; border-radius: 4px;
                }
            """
        else:
            return """
                QPushButton {
                    background-color: #333; color: #00E676; font-weight: bold;
                    border: 1px solid #555; border-radius: 4px;
                }
                QPushButton:hover { border: 1px solid #00E676; }
            """

    def toggle_sector(self, s_id, checked):
        self.core.toggle_isolation(s_id)

        # Update Button Visual
        btn = self.buttons[s_id]
        if checked:
            btn.setText(f"RECONNECT: {s_id}")
            btn.setStyleSheet(self.get_btn_style(True))
        else:
            btn.setText(f"ISOLATE: {s_id}")
            btn.setStyleSheet(self.get_btn_style(False))

        self.map_view.update()

    def sever_global(self):
        # Quick macro to kill the Gateway connection
        # Or isolate the gateway itself
        btn = self.buttons["NATIONAL_GATEWAY"]
        if not btn.isChecked():
            btn.click()  # Trigger toggle logic

    def game_tick(self):
        self.core.propagate_virus()

        # Update Stats
        clean, infected, isolated = self.core.get_stats()
        self.lbl_stats.setText(f"CLEAN: {clean} | INFECTED: {infected} | AIR-GAPPED: {isolated}")

        # Check Critical failure
        if self.core.sectors['MILITARY']['state'] == 'INFECTED':
            self.lbl_stats.setText("CRITICAL FAILURE: DEFENSE NET COMPROMISED")
            self.lbl_stats.setStyleSheet("color: #FF1744; font-size: 16px; font-weight: bold;")

        self.map_view.update()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = KillSwitchApp()
    window.show()
    sys.exit(app.exec_())