def main(tag):
    """Removes Python version and OS from Requirements.txt"""
    req_file = "requirements.txt"

    with open(req_file, "r") as file:
        lines = file.readlines()
        new_lines = []
        for i, line in enumerate(lines):
            new_line = line.split(";")[0].replace(" ", "")
            if "[" in new_line and "]" in new_line:
                new_line = new_line.split("[")[0] + new_line.split("]")[1]
            if i < len(lines) - 1:
                new_line += "\n"

            new_lines.append(new_line)

        with open(req_file, "w") as file:
            file.writelines(new_lines)
            print("Requirements file overwritten")
    file.close()


if __name__ == "__main__":
    main()
