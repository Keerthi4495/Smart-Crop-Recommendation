import mysql.connector
from db_config import DB_HOST, DB_USER, DB_PASSWORD, DB_NAME


def create_database():
    connection = mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
    )
    cursor = connection.cursor()
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME}")
    cursor.close()
    connection.close()


def create_tables():
    connection = mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
    )
    cursor = connection.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            email VARCHAR(100),
            password_hash VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS crop_predictions (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(50),
            nitrogen FLOAT,
            phosphorus FLOAT,
            potassium FLOAT,
            temperature FLOAT,
            humidity FLOAT,
            ph_value FLOAT,
            rainfall FLOAT,
            crop_name VARCHAR(50),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS crop_history (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            crop_name VARCHAR(50) NOT NULL,
            nitrogen FLOAT NOT NULL,
            phosphorus FLOAT NOT NULL,
            potassium FLOAT NOT NULL,
            temperature FLOAT NOT NULL,
            humidity FLOAT NOT NULL,
            ph_value FLOAT NOT NULL,
            rainfall FLOAT NOT NULL,
            location VARCHAR(255) NULL,
            estimated_cost DECIMAL(12, 2) NULL,
            estimated_revenue DECIMAL(12, 2) NULL,
            estimated_profit_loss DECIMAL(12, 2) NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_crop_history_user_created (user_id, created_at),
            CONSTRAINT fk_crop_history_user
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """
    )

    cursor.execute("ALTER TABLE crop_predictions ADD COLUMN IF NOT EXISTS username VARCHAR(50)")
    cursor.execute("ALTER TABLE crop_predictions ADD COLUMN IF NOT EXISTS nitrogen FLOAT")
    cursor.execute("ALTER TABLE crop_predictions ADD COLUMN IF NOT EXISTS phosphorus FLOAT")
    cursor.execute("ALTER TABLE crop_predictions ADD COLUMN IF NOT EXISTS potassium FLOAT")
    cursor.execute("ALTER TABLE crop_predictions ADD COLUMN IF NOT EXISTS temperature FLOAT")
    cursor.execute("ALTER TABLE crop_predictions ADD COLUMN IF NOT EXISTS humidity FLOAT")
    cursor.execute("ALTER TABLE crop_predictions ADD COLUMN IF NOT EXISTS ph_value FLOAT")
    cursor.execute("ALTER TABLE crop_predictions ADD COLUMN IF NOT EXISTS rainfall FLOAT")
    cursor.execute("ALTER TABLE crop_predictions ADD COLUMN IF NOT EXISTS crop_name VARCHAR(50)")

    connection.commit()
    cursor.close()
    connection.close()


if __name__ == "__main__":
    create_database()
    create_tables()
    print("MySQL database and tables are ready.")
