"""
This modules provides file managing for the telegram bot.
It will handle the data bases safe, and check their integrity.
User will have option to load custom path/to/folder where dat will be stored
db_handler will handle infrequent collisions via Optimistic Concurrency.
"""

# Import modules
import os
import json

# Import project-related modules

import bot_logger
import config

# Queue dict

queue = {}

# Helper Functions DO NOT USE THIS FUNCTIONS! THEY ONLY WORK IN MAIN FUNCTIONS!

def is_path_exist(path_to_dir):
    """Check that path is exist."""
    return os.path.exists(str(path_to_dir))

def create_files(path_to_dir, files):
    created_files = []
    for file in files:
        with open(os.path.join(path_to_dir, file), "w") as f:
            pass
        created_files.append(file)
    return created_files

def delete_files(path_to_dir, files):
    deleted_files = []
    for file in files:
        filepath = os.path.join(path_to_dir, file)
        os.remove(filepath)
        deleted_files.append(file)
    return deleted_files

def verbose_edit_files(files_list, action_type):
    """Print verbose information about created files."""
    if action_type == 0:
        action = "created"
    else:
        action = "deleted"
    print(".............................................")
    text = f"{action.title()} files:"
    for file in files_list:
        text += f"\n\t{file}"
    text += f"\n\nTotal files {action}: {len(files_list)}"
    print(text)
    print(".............................................")

def load_file(filename, path_to_dir):
    """
    Load user data from JSON-file and
    return it as loaded_file value.
    """
    loaded_file = {}
    file = os.path.join(path_to_dir, filename)
    try:
        with open(file) as f:
            read_file = f.read()
    except FileNotFoundError:
        with open(file, "w") as f:
            pass
        loaded_file = {}
        bot_logger.log_action("FILE LOAD", f"{file} is missing!")
    else:
        if read_file:
            loaded_file = json.loads(read_file)
        else:
            bot_logger.log_action("FILE LOAD", f"{file} is empty!")
            loaded_file = {}
        return loaded_file

def dump_file(data, filename, path_to_dir):
    """"""
    file = os.path.join(path_to_dir, filename)
    with open(file, "w") as f:
        json.dump(data, f)

def update_file(data, filename, path_to_dir, rewrite = False):
    """
    Extract, modify and dump data to a file.
    Has append and write options.
    """
    # Load data
    upd_data = load_file(filename, path_to_dir)
    # Modify data
    if rewrite:
        upd_data.clear()
        upd_data.update(data)
        dump_file(upd_data, filename, path_to_dir)
    else:
        try:
            upd_data.update(data)
        except AttributeError:
            upd_data = data
        # Store data
        dump_file(upd_data, filename, path_to_dir)


# Main Functions

def init_db(
    path_to_dir,
    required_files,
    verbose=False,
    strict_mode=False,
    forced=False,
):
    """
    Make sure that every required file is in place,
    otherwise will create new files if strict_mode is False.
    If strict_mode is True will raise an error
    in case some files are missing.
    """
    # Check if directory exist
    if not is_path_exist(path_to_dir):
        bot_logger.log_action("intergrity check",
                   f"{path_to_dir} and all files are missing!"
        )
        if strict_mode:
            raise RuntimeError("Missing a directory!")
        else:
            os.makedirs(os.path.dirname(path_to_dir), exist_ok=False)
            bot_logger.log_action("intergrity check", "Creating a new directory")
            create_files(path_to_dir, required_files)
            bot_logger.log_action("intergrity check", "Creating new files")

            if verbose:
                verbose_edit_files(required_files, 0)

    else:
        bot_logger.log_action("intergrity check", f"{path_to_dir} exists")
        # Check if files are missing
        dir_list = os.listdir(path_to_dir)
        if dir_list == []:
            if strict_mode:
                raise RuntimeError("Directory is empty!")
            else:
                bot_logger.log_action("intergrity check", f"{path_to_dir} is empty")
                create_files(path_to_dir, required_files)
                dir_list = os.listdir(path_to_dir)
                bot_logger.log_action("intergrity check", "Creating new files")

                if verbose:
                    verbose_edit_files(required_files, 0)

        elif sorted(dir_list) != sorted(required_files):
            missing_files = list(set(required_files) - set(dir_list))
            other_files = list(set(dir_list) - set(required_files))
            cfiles = []
            dfiles = []
            if missing_files:
                bot_logger.log_action("intergrity check",
                    "Some required files are missing")
                bot_logger.log_action("intergrity check", "Creating new files")
                cfiles = create_files(path_to_dir, missing_files)
            if other_files:
                if forced:
                    bot_logger.log_action("intergrity check", "Deleting other files")
                    dfiles = delete_files(path_to_dir, other_files)
                else:
                    bot_logger.log_action("intergrity check", "Other files are present")
                    print("------------------------------------")
                    print("Will delete these files:")
                    for file in other_files:
                        print(f"\t{file}")
                    print("------------------------------------")
                    delete_prompt = input("Do you wish to delete these files? (y/n): ")
                    if delete_prompt == "y":
                        bot_logger.log_action("intergrity check", "Deleting other files")
                        dfiles = delete_files(path_to_dir, other_files)
                    else:
                        bot_logger.log_action("intergrity check",
                                   "Other files are NOT removed files")
            if verbose:
                verbose_edit_files(cfiles, 0)
                verbose_edit_files(dfiles, 1)

        elif sorted(dir_list) == sorted(required_files):
            bot_logger.log_action("intergrity check", "All required files exist")

def load_db(db_name):
    """Loads db, using dbh's load_file."""
    filename = None
    for file in config.REQUIRED_FILES:
        if os.path.splitext(file)[0] == db_name:
            filename = file
    if not filename:
        bot_logger.log_action("load_db",
            f"No file named {db_name}!\nReturning empty dict!")
        return {}
    loaded_db = load_file(filename,config.PATH_TO_DIR)
    return loaded_db

def update_db(data, db_name, rewrite=False):
    """Form a request and append it to queue for file update."""
    filename = None
    for file in config.REQUIRED_FILES:
        if os.path.splitext(file)[0] == db_name:
            filename = file
    if not filename:
        bot_logger.log_action("load_db",
            f"No file named {db_name}!\nUpdate interrupted!")
        return
    timestamp = time.time_ns()
    # Form request
    request = {
        timestamp:{
            "filename":[filename,config.PATH_TO_DIR],
            "data":data,
            "rewrite":rewrite,
        }
    }
    # Append request to queue
    queue.update(request)
    bot_logger.log_action("update request",f"{db_name} request loaded!")

def poll():
    """Check only one request in the queue."""
    if queue:
        request = None
        # Decompose earliest request
        first_request_key = min(queue.keys())
        try:
            request = queue.pop(first_request_key)
        except TypeError:
            return
        filename = request["filename"][0]
        path_to_dir = request["filename"][1]
        data = request["data"]
        # Process the update request
        update_file(data=data,
                    filename=filename,
                    path_to_dir=path_to_dir,rewrite=request["rewrite"]
        )
        bot_logger.log_action("update process",
            f"{filename} has been updated!")

def main():
    """Init the handler and start main loop."""
    init_db(config.PATH_TO_DIR,config.REQUIRED_FILES,verbose=True)

if __name__ == "__main__":
    main()
