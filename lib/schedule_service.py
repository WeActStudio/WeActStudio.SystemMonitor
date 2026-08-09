import win32com.client  

def task_exists(task_name):  
    """  
    检查指定的任务名称是否存在于任务计划程序中。  
  
    参数:  
    task_name (str): 要检查的任务名称。  
  
    返回:  
    bool: 如果任务存在，则返回True；否则返回False。  
    """  
    # 连接到任务计划程序  
    scheduler = win32com.client.Dispatch("Schedule.Service")  
    scheduler.Connect()  
  
    # 假设我们检查根目录下的任务（你也可以检查其他文件夹）  
    root_folder = scheduler.GetFolder("\\")  
    
    Path = None

    # 遍历任务  
    for task in root_folder.GetTasks(0):  # 0 表示返回所有任务  
        if task.Name == task_name:  
            if len(task.Definition.Actions) == 1:
                Path = task.Definition.Actions[0].Path
            return True,Path
  
    # 如果没有找到任务  
    return False,Path

def delete_task(task_name, folder_path="\\"):  
    """  
    删除指定的计划任务。  
  
    参数:  
    task_name (str): 要删除的任务的名称。  
    folder_path (str): 包含任务的文件夹路径，默认为根文件夹("\\")。  
  
    返回:  
    bool: 如果任务成功删除，则返回True；如果任务不存在或删除失败，则返回False。  
    """  
    try:  
        # 连接到任务计划程序  
        scheduler = win32com.client.Dispatch("Schedule.Service")  
        scheduler.Connect()  
  
        # 获取包含任务的文件夹  
        folder = scheduler.GetFolder(folder_path)  
  
        # 尝试找到并删除任务  
        folder.DeleteTask(task_name, 0)  # 第二个参数是标志，0 表示正常删除  
  
        print(f"task '{task_name}' delete ok")  
        return True  
  
    except Exception as e:  
        print(f"error '{task_name}': {e}")  
        return False  
    
def create_login_task(task_name, script_path, arguments=""):  
    scheduler = win32com.client.Dispatch("Schedule.Service")  
    scheduler.Connect()  
  
    root_folder = scheduler.GetFolder("\\")  
    task_def = scheduler.NewTask(0)  
  
    # 设置任务的基本信息（可选）  
    registration_info = task_def.RegistrationInfo  
    registration_info.Description = f"Task to run {task_name} on user login"  
    registration_info.Author = "WeAct Studio"  
  
    # 创建一个触发器，设置为用户登录时触发  
    trigger = task_def.Triggers.Create(9)  # 9 表示在用户登录时触发  
    trigger.Enabled = True  
  
    # 设置操作（即要执行的命令）  
    action = task_def.Actions.Create(0)  # 0 表示执行操作  
    action.Path = script_path 
    if arguments != "":
        action.Arguments = arguments
  
    # 设置任务以管理员权限运行  
    principal = task_def.Principal  
    principal.RunLevel  = 1  

    settings = task_def.Settings
    settings.StopIfGoingOnBatteries = False
    settings.DisallowStartIfOnBatteries = False

  
    # 注意：在某些情况下，你可能不需要显式设置LogonType为6，因为UserId为"NT AUTHORITY\\SYSTEM"已经隐含了这一点。  
    # 但是，为了清晰起见，我还是在这里包含了它。  
  
    # 注册任务  
    try:  
        root_folder.RegisterTaskDefinition(  
            task_name,  
            task_def,  
            6,  # TASK_CREATE（如果任务已存在，则抛出异常）  
            "",  
            "",  
            3
        )  
        # 注意：上面的TASK_LOGON_SERVICE_ACCOUNT可能不是必需的，因为我们已经通过Principal.UserId设置了权限。  
        # 但是，为了与RegisterTaskDefinition的参数保持一致，我保留了它。在实际代码中，你可能需要将其替换为None或省略。  
        print(f"Task '{task_name}' created successfully for user login.")  
    except Exception as e:  
        print(f"Failed to create task '{task_name}': {e}")  
  