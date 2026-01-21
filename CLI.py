# todo.py
tasks = []

def show_tasks():
    print("\nTasks:")
    for idx, task in enumerate(tasks, 1):
        print(f"{idx}. {task}")

while True:
    command = input("\nEnter command (add/show/exit): ").strip().lower()
    if command == "add":
        task = input("Enter a task: ")
        tasks.append(task)
    elif command == "show":
        show_tasks()
    elif command == "exit":
        break
    else:
        print("Invalid command.")
