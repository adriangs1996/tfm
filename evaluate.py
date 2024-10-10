def get_right_category_from_file_name(file_name):
    return file_name.split('/')[-2].split('.')[0]


if __name__ == '__main__':
    from run import scan_folder
    total = 0
    correct = 0
    wrongs = []
    folder = 'examples'
    rights = []
    for file_path, category in scan_folder(folder):
        total += 1
        if get_right_category_from_file_name(file_path) == category:
            correct += 1
            rights.append((file_path, category))
        else:
            wrongs.append((file_path, category, get_right_category_from_file_name(file_path)))

    # Create the confusion matrix for the categories
    matrix = {}
    for right in rights:
        if right[1] not in matrix:
            matrix[right[1]] = {}
        for wrong in wrongs:
            if wrong[2] not in matrix[right[1]]:
                matrix[right[1]][wrong[2]] = 0
            if wrong[0] == right[0]:
                matrix[right[1]][wrong[2]] += 1

    print("Confusion Matrix")
    for row_label, row in matrix.items():
        print(f"{row_label}: {row}")

    print(f"Total: {total}, Correct: {correct}, Accuracy: {correct/total}")
    for wrong in wrongs:
        print(f"File: {wrong[0]}, Predicted: {wrong[1]}, Actual: {wrong[2]}")
