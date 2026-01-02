from .db import connect, init_schema

def main():
    conn = connect()
    init_schema(conn)
    conn.close()
    print("DB_OK")

if __name__ == "__main__":
    main()
