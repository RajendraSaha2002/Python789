import sys
import pandas as pd
import sqlalchemy
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QLabel, QPushButton, QTableWidget,
                             QTableWidgetItem, QHeaderView)
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression
import numpy as np

# DB CONFIG
db_engine = sqlalchemy.create_engine('postgresql+psycopg2://postgres:varrie75@localhost/postgres')


class PredictiveDashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Smart Warehouse Analytics & AI Prediction")
        self.setGeometry(100, 100, 1200, 800)
        self.setStyleSheet("background-color: #2c3e50; color: white;")

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)

        # Header
        header = QLabel("🧠 Inventory AI Command Center")
        header.setStyleSheet("font-size: 24px; font-weight: bold; padding: 10px; color: #ecf0f1;")
        layout.addWidget(header)

        # Content Split
        content_layout = QHBoxLayout()

        # Left: Prediction Table
        left_layout = QVBoxLayout()
        self.pred_table = QTableWidget()
        self.pred_table.setColumnCount(3)
        self.pred_table.setHorizontalHeaderLabels(["Product", "Predicted Stock (7 Days)", "Risk Level"])
        self.pred_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.pred_table.setStyleSheet("color: black; background-color: white;")
        left_layout.addWidget(self.pred_table)

        btn_predict = QPushButton("Run AI Prediction Model")
        btn_predict.setStyleSheet("background-color: #e67e22; font-weight: bold; padding: 10px;")
        btn_predict.clicked.connect(self.run_prediction_model)
        left_layout.addWidget(btn_predict)

        content_layout.addLayout(left_layout, 1)

        # Right: Graph
        self.figure, self.ax = plt.subplots()
        self.canvas = FigureCanvas(self.figure)
        content_layout.addWidget(self.canvas, 1)

        layout.addLayout(content_layout)

    def run_query(self, sql):
        with db_engine.connect() as conn:
            return pd.read_sql(sql, conn)

    def run_prediction_model(self):
        # 1. Get Sales History for Electronics
        # Note: In real life, iterate all products. Here we focus on Product ID 1 (Mouse)
        query = """
                SELECT EXTRACT(DOY FROM log_timestamp) as day_of_year, SUM(change_amount) as daily_change
                FROM inventory_logs
                WHERE product_id = 1 \
                  AND change_amount < 0
                GROUP BY day_of_year \
                ORDER BY day_of_year \
                """
        df = self.run_query(query)

        if df.empty:
            print("No history for prediction")
            return

        # 2. Prepare ML Data (Simple Linear Regression)
        # X = Day, y = Accumulated Stock Level (simulated reverse calculation)
        df['cumulative_sales'] = df['daily_change'].cumsum()

        X = df['day_of_year'].values.reshape(-1, 1)
        y = df['cumulative_sales'].values

        model = LinearRegression()
        model.fit(X, y)

        # Predict next 7 days
        last_day = X[-1][0]
        future_days = np.array([[last_day + i] for i in range(1, 8)])
        future_sales = model.predict(future_days)

        # Calculate current stock to offset prediction
        current_stock = self.run_query("SELECT stock_qty FROM products WHERE product_id=1")['stock_qty'][0]
        predicted_drain = future_sales[-1] - future_sales[0]  # Estimated loss over week
        final_stock = current_stock + predicted_drain  # drain is negative

        # 3. Update UI
        self.pred_table.setRowCount(1)
        self.pred_table.setItem(0, 0, QTableWidgetItem("Wireless Mouse"))
        self.pred_table.setItem(0, 1, QTableWidgetItem(f"{int(final_stock)}"))

        risk_item = QTableWidgetItem("NORMAL")
        if final_stock < 20:
            risk_item.setText("HIGH RISK")
            risk_item.setBackground(plt.cm.colors.to_hex((1, 0, 0, 1)))  # Red

        self.pred_table.setItem(0, 2, risk_item)

        # 4. Plot Trend
        self.ax.clear()
        self.ax.scatter(X, y, color='blue', label='Historical Sales')
        self.ax.plot(future_days, future_sales, color='red', linestyle='--', label='AI Forecast')
        self.ax.set_title("Inventory Depletion Forecast (Product #1)")
        self.ax.legend()
        self.ax.grid(True)
        self.canvas.draw()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PredictiveDashboard()
    window.show()
    sys.exit(app.exec())