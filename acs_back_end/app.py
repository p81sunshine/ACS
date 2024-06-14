from flask import Flask, request, jsonify
from pymongo import MongoClient
from bson.objectid import ObjectId
from flask_cors import CORS, cross_origin
from genetic import schedule_interface
from database import get_local_db, update_local_db
import copy
import threading
import time
import re  # 导入正则表达式模块
from threading import Event
import requests
import json

# 登录请求
login_url = "http://localhost:8000/api/user/login/"
login_data = {
    "number": "000000",
    "password": "8b44047b4fc99d0b69be05961d31a8e3bb6de5b005a9e723415b0d323f69b53f"
}

login_response = requests.post(login_url, data=login_data)
login_response_data = login_response.json()

print(login_response_data)

# 从登录响应的data字典中提取token
token = login_response_data['data'].get('token')

print(token)

# 使用提取的token发起课程列表请求，注意Authorization头的格式
course_list_url = "http://localhost:8000/api/course/list/"
headers = {
    "Authorization": token  # 注意这里的改动
}


# 添加用户列表请求，使用Authorization头
user_list_url = "http://localhost:8000/api/user/list/"
user_list_headers = {
    "Authorization": token
}

def get_teacher_from_mysql():
    user_list_response = requests.get(user_list_url, headers=user_list_headers)
    user_list_response_data = user_list_response.text
    data = json.loads(user_list_response_data)
    # 提取auth值为1的项（在这个例子中，不会找到任何匹配项）
    auth_one_items = [item for item in data['data'] if item['auth'] == 1]
    
    teachers_collection = []  # 创建一个空列表来收集所有符合条件的教师信息
    for item in auth_one_items:
        # 计算teacher_id
        teacher_id = int(item['number']) - 321010 + 36
        # 创建新的字典
        new_doc = {
            "teacher_id": teacher_id,
            "teacher_name": item['name']
        }
        teachers_collection.append(new_doc)  # 将新的字典添加到列表中

    return teachers_collection  # 返回包含所有符合条件教师信息的列表

def get_course_from_mysql():
    course_list_response = requests.get(course_list_url, headers=headers)
    course_list_response_data = course_list_response.json()
    # data = json.loads(course_list_response_data)  # 这行是不必要的，应该删除

    courses_collection = []  # 创建一个空列表来收集所有课程信息
    for item in course_list_response_data['data']:
        # 计算teacher_id
        teacher_id = int(item['teacher']) - 321010 + 36
        # 修正class_id的范围
        class_id = int(item['id']) - 1
        # 创建新的字典
        new_doc = {
            "class_id": class_id,
            "teacher_id": teacher_id,
            "class_name": item['name'],
            "campus_id": item['campus']
        }
        courses_collection.append(new_doc)  # 将新的字典添加到列表中

    return courses_collection  # 返回包含所有课程信息的列表

#schedule_done = Event()
app = Flask(__name__)
cors = CORS(app)

uri = "mongodb+srv://3210102495:Gw7GaKXlOuMWQ1bf@cluster0.pheotiv.mongodb.net/"
client = MongoClient(uri)

# 在应用启动时下载所有数据
database = client['scheduling_course']
schedule_res_collection = database['schedule_res']
courses_collection = get_course_from_mysql()
campus_collection = database['campus']
teacher_collection = get_teacher_from_mysql()
classrooms_collection = database['classrooms']
time_slots_collection = database['time_slots']  # 新增

courses = get_course_from_mysql()
teacher = get_teacher_from_mysql()
schedule_res = list(schedule_res_collection.find({}))
campus = list(campus_collection.find({}))
classrooms = list(classrooms_collection.find({}))
time_slots = list(time_slots_collection.find({}))  # 新增
update_local_db(schedule_res, courses, campus, teacher, classrooms, time_slots)

def update_mongodb():
    local_db_schedule_res, local_db_courses, local_db_campus, local_db_teacher, local_db_classrooms, local_db_time_slots = get_local_db()
    # 删除 MongoDB 中的原有排课表
    #schedule_done.wait()
    schedule_res_collection.delete_many({})

    # 将本地数据写入 MongoDB
    for document in local_db_schedule_res:
        schedule_res_collection.insert_one(document)

    print("Schedule result update completed successfully.")

# 新的接口URL
modify_course_list_url = "http://localhost:8000/api/course/modify_list/"

def modify_course_list_with_schedule(schedule_res):
    # 获取课程列表
    course_list_response = requests.get(course_list_url, headers=headers)
    course_list_response_data = course_list_response.json()
    
    # 准备一次性将所有课程的时间字段设置为default的列表
    courses_to_set_default = []
    for course in course_list_response_data['data']:
        courses_to_set_default.append({
            "id": course['id'],
            "name": course['name'],
            "teacher": course['teacher'],
            "credit": course['credit'],
            "content": course['content'],
            "total": course['total'],
            "check_rule": course['check_rule'],
            "time": "default",  # 假设我们要修改的字段是时间
            "campus":course['campus']
        })
    
    # 发起一次性将所有课程时间设置为default的请求
    requests.post(modify_course_list_url, json={"courses": courses_to_set_default}, headers=user_list_headers)
    
    # 准备根据schedule_res修改的课程数据列表
    courses_to_modify = []
    for schedule in schedule_res:
        class_id = schedule['class_id']
        new_time = schedule['time']
        
        # 从课程列表中找到对应的课程
        course_to_modify = next((item for item in courses_to_set_default if item['id'] == class_id+1), None)
        
        if not course_to_modify:
            print(f"未找到指定ID({class_id})的课程")
            continue
        
        # 根据当前字段值更新时间字段
        existing_time = course_to_modify['time']
        if existing_time == "default":
            course_to_modify['time'] = new_time
        else:
            course_to_modify['time'] = existing_time + ";" + new_time
        
        # 注意：这里不需要再次添加到修改列表，因为courses_to_set_default已经被更新
        
    # 发起一次性修改请求
    modify_response = requests.post(modify_course_list_url, json={"courses": courses_to_set_default}, headers=user_list_headers)
    print(modify_response.text)

def reschedule():
    schedule_interface()
    local_db_schedule_res, local_db_courses, local_db_campus, local_db_teacher, local_db_classrooms, local_db_time_slots = get_local_db()
    schedule_res = local_db_schedule_res.copy()  # 使用本地数据

    # 在新线程中更新 MongoDB
    threading.Thread(target=update_mongodb).start()
    threading.Thread(target=modify_course_list_with_schedule(schedule_res)).start()

reschedule()
# 创建一个锁
data_lock = threading.Lock()
global next_classroom_id  

def update_local_db_from_mongodb():
    while True:
        with data_lock:  # 获取锁
            schedule_res = list(schedule_res_collection.find({}))
            courses = get_course_from_mysql()
            campus = list(campus_collection.find({}))
            teacher = get_teacher_from_mysql()
            classrooms = list(classrooms_collection.find({}))
            time_slots = list(time_slots_collection.find({}))  # 新增
            update_local_db(schedule_res, courses, campus, teacher, classrooms, time_slots)
        
        print("Updated local database at", time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()))  # 打印更新时间
        time.sleep(60)  # 每60秒更新一次数据

update_thread = threading.Thread(target=update_local_db_from_mongodb)
update_thread.start()

# 获取课室信息
@app.route('/api/classrooms', methods=['GET'])
@cross_origin()
def get_classrooms():
    try:
        local_db_schedule_res, local_db_courses, local_db_campus, local_db_teacher, local_db_classrooms, local_db_time_slots = get_local_db()
        classes = copy.deepcopy(local_db_classrooms)

        result = []  # 创建一个新的结果列表

        # 将设备数组转换为字符串，并删除 _id 字段
        for i in range(len(classes)):
            equipment = ', '.join(classes[i]['equipment'])
            del classes[i]['_id']  # 删除 _id 字段

            # 创建一个新的字典，并添加到结果列表中
            result.append({
                "id": classes[i]['classroom_id'],
                "name": classes[i]['classroom_name'],
                "campus_id": classes[i]['campus_id'],
                "capacity": classes[i]['capacity'],
                "equipment": equipment
            })

        return jsonify(result)  # 返回结果到前端
    except Exception as e:
        print('An error occurred while trying to connect to MongoDB', e)
        return jsonify({"message": "An error occurred while trying to connect to MongoDB", "data": []}), 500
    
@app.route('/api/classrooms/name/<int:classroom_id>', methods=['GET'])
@cross_origin()
def get_classroom_name(classroom_id):
    try:
        local_db_schedule_res, local_db_courses, local_db_campus, local_db_teacher, local_db_classrooms, local_db_time_slots = get_local_db()
        classrooms = copy.deepcopy(local_db_classrooms)

        # 在教室列表中查找匹配的教室ID
        for classroom in classrooms:
            if classroom['classroom_id'] == classroom_id:
                return jsonify({"name": classroom['classroom_name']})  # 返回教室名称

        # 如果没有找到匹配的教室ID，返回一个错误消息
        return jsonify({"message": f"No classroom found with ID {classroom_id}"}), 404
    except Exception as e:
        print('An error occurred while trying to connect to MongoDB', e)
        return jsonify({"message": "An error occurred while trying to connect to MongoDB"}), 500

@app.route('/api/test/searchid', methods=['POST'])
@cross_origin()
def search_id():
    try:
        name = request.json['name']  # 从请求的JSON体中提取名字
        print(f"Received name: {name}")  # 打印接收到的名字

        teachers = get_teacher_from_mysql()

        id = -1  # 假设没有找到结果
        for teacher in teachers:
            teacher_name = teacher['teacher_name'].strip().replace("'", '"')  # 从teacher字典中提取出teacher_name，去除两端的空格，将单引号替换为双引号
            print(f"Checking teacher: {teacher_name}")  # 打印正在检查的教师名字
            if teacher_name == name:
                id = teacher['teacher_id']
                print(f"Found matching teacher: {teacher_name}")  # 打印找到的匹配教师名字
                break  # 找到匹配的教师后立即退出循环

        return jsonify({"success": True, "id": id})  # 返回JSON响应
    except Exception as e:
        print('An error occurred while trying to connect to MongoDB', e)
        return jsonify({"success": False, "id": -1}), 500
    
@app.route('/api/teacher/name/<int:teacher_id>', methods=['GET'])
@cross_origin()
def get_teacher_name(teacher_id):
    try:
        teachers = get_teacher_from_mysql()

        # 在教师列表中查找匹配的教师ID
        for teacher in teachers:
            if teacher['teacher_id'] == teacher_id:
                return jsonify({"name": teacher['teacher_name']})  # 返回教师姓名

        # 如果没有找到匹配的教师ID，返回一个错误消息
        return jsonify({"message": f"No teacher found with ID {teacher_id}"}), 404
    except Exception as e:
        print('An error occurred while trying to connect to MongoDB', e)
        return jsonify({"message": "An error occurred while trying to connect to MongoDB"}), 500


@app.route('/api/classrooms/courses/<int:classroom_id>', methods=['GET'])
@cross_origin()
def get_classroom_courses(classroom_id):
    try:
        local_db_schedule_res, local_db_courses, local_db_campus, local_db_teacher, local_db_classrooms, local_db_time_slots = get_local_db()
        classroom_courses = [item for item in local_db_schedule_res if item['classroom'] == classroom_id]
        result = {"courses": []}

        mysql_courses = get_course_from_mysql()
        mysql_teacher = get_teacher_from_mysql()

        for i in range(len(classroom_courses)):
            course = next((item for item in mysql_courses if item['class_id'] == classroom_courses[i]['class_id']), None)
            classroom = next((item for item in local_db_classrooms if item['classroom_id'] == classroom_courses[i]['classroom']), None)
            campus = next((item for item in local_db_campus if item['name'] == course['campus_id']), None) if course else None
            teacher = next((item for item in mysql_teacher if item['teacher_id'] == classroom_courses[i]['teacher']), None)
            time_slot = next((item for item in local_db_time_slots if item['time'] == classroom_courses[i]['time']), None)

            if None in [teacher, course, classroom, campus, time_slot]:
                continue

            result["courses"].append({
                "schedule_id": classroom_courses[i]['schedule_id'],
                "course_id": classroom_courses[i]['class_id'],
                "classroom_id": classroom_courses[i]['classroom'],
                "name": course['class_name'],
                "classroom": classroom['classroom_name'],
                "campus": campus['name'],
                "capacity": classroom['capacity'],
                "time_slot": time_slot['time_slot'],
                "teacher": teacher['teacher_name']
            })

        return jsonify(result)  # 返回结果到前端

    except Exception as e:
        print('An error occurred while trying to get courses', e)
        return jsonify({"message": "An error occurred while trying to get courses", "data": []}), 500
            

@app.route('/api/classrooms', methods=['POST'])
@cross_origin()
def create_classroom():
    global next_classroom_id  # 声明 next_classroom_id 为全局变量
    try:
        local_db_schedule_res, local_db_courses, local_db_campus, local_db_teacher, local_db_classrooms, local_db_time_slots = get_local_db()
        # 从请求体中获取教室信息
        classroom_info = request.json

        # 检查 classroom_info 是否包含所有必需的键
        required_keys = ['classroomName', 'campus', 'capacity', 'equipment']
        if not all(key in classroom_info for key in required_keys):
            return jsonify({"message": "Missing required fields in request body", "data": []}), 400

        # 检查 'classroomName' 是否为字符串
        if not isinstance(classroom_info['classroomName'], str):
            return jsonify({"message": "Invalid data type for 'classroomName'", "data": []}), 400

        # 检查 'classroomName' 是否符合 "xxx-xxx" 的格式
        # -之前的字符串必须汉字开头，且只能包括汉字，字母和数字，长度大于等于2，小于等于10
        # -后的字符串只能包含数字，长度大于等于3，小于等于4
        if not re.match(r'^[\u4e00-\u9fa5][\u4e00-\u9fa5a-zA-Z0-9]{1,9}-\d{3,4}$', classroom_info['classroomName']):
            return jsonify({"message": "Invalid format for 'classroomName'. It should be in the format 'xxx-xxx', where 'xxx' is a string starting with a Chinese character and containing only Chinese characters, letters, and numbers with length between 2 and 10, and 'xxx' is a string containing only numbers with length between 3 and 4.", "data": []}), 400

        # 检查 'campus' 是否为字符串
        if not isinstance(classroom_info['campus'], str):
            return jsonify({"message": "Invalid data type for 'campus'", "data": []}), 400

        # 检查 'capacity' 是否为整数
        if not isinstance(classroom_info['capacity'], int):
            return jsonify({"message": "Invalid data type for 'capacity'", "data": []}), 400

        # 检查 'equipment' 是否为字符串数组
        if not isinstance(classroom_info['equipment'], list) or not all(isinstance(item, str) for item in classroom_info['equipment']):
            return jsonify({"message": "Invalid data type for 'equipment'", "data": []}), 400

        # 查询 campus_id
        campus = next((item for item in local_db_campus if item["name"] == classroom_info['campus']), None)
        if campus is None:
            return jsonify({"message": f"No campus found with name: {classroom_info['campus']}", "data": []}), 404
        campus_id = campus['campus_id']

        # 更新 next_classroom_id
        if local_db_classrooms:
            next_classroom_id = max(classroom['classroom_id'] for classroom in local_db_classrooms) + 1
        else:
            next_classroom_id = 1

         # 自动生成 classroom_id
        classroom_id = next_classroom_id

        # 调整数据格式
        classroom_info = {
            'classroom_id': classroom_id,
            'classroom_name': classroom_info['classroomName'],
            'campus_id': campus_id,
            'capacity': classroom_info['capacity'],
            'equipment': classroom_info['equipment'],
        }
        
        # 检查是否已经存在具有相同 classroom_name 和 campus_id 的教室
        existing_classroom = next((item for item in local_db_classrooms if item["classroom_name"] == classroom_info['classroom_name'] and item["campus_id"] == campus_id), None)
        if existing_classroom is not None:
            # 如果 classroom_name 和 campus_id 都相同，拒绝插入新的教室
            return jsonify({"message": "Classroom with the same name and campus already exists. Insertion is denied.", "data": []}), 400
        else:
            # 插入新的教室
            result = classrooms_collection.insert_one(classroom_info)
            # 在后台更新本地数据库
            def update_local_db():
                with data_lock:  # 获取锁
                    # 从 MongoDB 获取新插入的教室的完整信息
                    new_classroom = classrooms_collection.find_one({'_id': result.inserted_id})
                    local_db_classrooms.append(new_classroom)
            threading.Thread(target=update_local_db).start()
            classroom_info.pop('_id', None)  # 删除 _id 字段
            return jsonify({"message": "success", "data": [classroom_info]}), 201
    except Exception as e:
        print('An error occurred while trying to connect to MongoDB', e)
        return jsonify({"message": "An error occurred while trying to connect to MongoDB", "data": []}), 500
    
@app.route('/api/classrooms/<int:id>', methods=['DELETE'])
@cross_origin()
def delete_classroom(id):
    try:
        local_db_schedule_res, local_db_courses, local_db_campus, local_db_teacher, local_db_classrooms, local_db_time_slots = get_local_db()
        # 查询并删除教室
        result = classrooms_collection.delete_one({'classroom_id': id})

        if result.deleted_count == 0:
            # 如果没有删除任何教室，返回 404 状态码
            return jsonify({"message": f"No classroom found with id: {id}", "data": []}), 404
        else:
            # 如果成功删除教室，更新本地数据库
            with data_lock:  # 获取锁
                local_db_classrooms[:] = [d for d in local_db_classrooms if d.get('classroom_id') != id]
                # 在后台调用遗传算法重新排课

            schedule_interface()
            
            # 在后台更新数据库
            with data_lock:  # 获取锁
                update_thread = threading.Thread(target=update_mongodb)  # 创建新线程
                update_thread.start()  # 开始新线程
            
            return jsonify({"message": f"Successfully deleted classroom with id: {id}", "data": []}), 200
    except Exception as e:
        print('An error occurred while trying to connect to MongoDB', e)
        return jsonify({"message": "An error occurred while trying to connect to MongoDB", "data": []}), 500


@app.route('/api/classrooms/<int:id>', methods=['PUT'])
@cross_origin()
def update_classroom(id):
    try:
        local_db_schedule_res, local_db_courses, local_db_campus, local_db_teacher, local_db_classrooms, local_db_time_slots = get_local_db()
        # 获取请求中的参数
        classroom_name = request.json.get('classroomName')
        campus_name = request.json.get('campus')
        equipment = request.json.get('equipment')

        # 检查 'id' 是否为整数
        if not isinstance(id, int):
            return jsonify({"message": "Invalid data type for 'id'", "data": []}), 400

        # 检查 'classroomName' 是否为字符串
        if classroom_name is not None and not isinstance(classroom_name, str):
            return jsonify({"message": "Invalid data type for 'classroomName'", "data": []}), 400

        # 检查 'classroomName' 是否符合 "xxx-xxx" 的格式
        # -之前的字符串必须汉字开头，且只能包括汉字，字母和数字，长度大于等于2，小于等于10
        # -后的字符串只能包含数字，长度大于等于3，小于等于4
        if classroom_name is not None and not re.match(r'^[\u4e00-\u9fa5][\u4e00-\u9fa5a-zA-Z0-9]{1,9}-\d{3,4}$', classroom_name):
            return jsonify({"message": "Invalid format for 'classroomName'. It should be in the format 'xxx-xxx', where 'xxx' is a string starting with a Chinese character and containing only Chinese characters, letters, and numbers with length between 2 and 10, and 'xxx' is a string containing only numbers with length between 3 and 4.", "data": []}), 400

        # 检查 'campus' 是否为字符串
        if campus_name is not None and not isinstance(campus_name, str):
            return jsonify({"message": "Invalid data type for 'campus'", "data": []}), 400

        # 检查 'equipment' 是否为字符串数组
        if equipment is not None and (not isinstance(equipment, list) or not all(isinstance(item, str) for item in equipment)):
            return jsonify({"message": "Invalid data type for 'equipment'", "data": []}), 400

        # 从本地数据中用campus字段查询相应campus_id
        campus = next((item for item in local_db_campus if item["name"] == campus_name), None)
        if campus is None:
            return jsonify({"message": f"No campus found with name: {campus_name}", "data": []}), 404
        campus_id = campus['campus_id']

        # 检查是否存在具有相同名称和校区的教室
        existing_classroom = next((item for item in local_db_classrooms if item["classroom_name"] == classroom_name and item["campus_id"] == campus_id), None)
        if existing_classroom is not None and existing_classroom["classroom_id"] != id:
            # 如果存在，并且不是正在更新的教室，则拒绝更新
            return jsonify({"message": "A classroom with the same name and campus already exists.", "data": []}), 400

        # 构建更新的数据
        update_data = {}
        if classroom_name is not None:
            update_data['classroom_name'] = classroom_name
        if campus_id is not None:
            update_data['campus_id'] = campus_id
        if equipment is not None:
            update_data['equipment'] = equipment

        # 查找匹配的教室
        classroom = next((item for item in local_db_classrooms if item["classroom_id"] == id), None)

        if classroom is None:
            # 如果没有找到匹配的教室，返回 404 状态码
            return jsonify({"message": f"No classroom found with id: {id}", "data": []}), 404
        else:
            # 检查新的数据是否与现有的数据相同
            if classroom['classroom_name'] == classroom_name and classroom['campus_id'] == campus_id and classroom['equipment'] == equipment:
                return jsonify({"message": "The classroom information is already up to date", "data": []}), 400

            # 更新本地数据库
            with data_lock:
                # 更新本地数据库中的教室信息
                for item in local_db_classrooms:
                    if item["classroom_id"] == id:
                        item.update(update_data)
                update_local_db(local_db_schedule_res, local_db_courses, local_db_campus, local_db_teacher, local_db_classrooms, local_db_time_slots)

            # 更新 MongoDB
            def update_mongodb_classrooms():
                classrooms_collection.update_one({'classroom_id': id}, {'$set': update_data})

            update_thread = threading.Thread(target=update_mongodb_classrooms)
            update_thread.start()

            return jsonify({"message": f"Successfully updated classroom with id: {id}", "data": []}), 200
    except Exception as e:
        print('An error occurred while trying to update classroom', e)
        return jsonify({"message": "An error occurred while trying to update classroom", "data": []}), 500

@app.route('/api/teacher/courses/<int:teacher_id>', methods=['GET'])
@cross_origin()
def get_courses(teacher_id):
    try:
        local_db_schedule_res, local_db_courses, local_db_campus, local_db_teacher, local_db_classrooms, local_db_time_slots = get_local_db()
        courses = [item for item in local_db_schedule_res if item['teacher'] == teacher_id]
        result = {"courses": []}

        mysql_courses = get_course_from_mysql()
        mysql_teacher = get_teacher_from_mysql()

        for i in range(len(courses)):
            course = next((item for item in mysql_courses if item['class_id'] == courses[i]['class_id']), None)
            classroom = next((item for item in local_db_classrooms if item['classroom_id'] == courses[i]['classroom']), None)
            campus = next((item for item in local_db_campus if item['name'] == course['campus_id']), None) if course else None
            teacher = next((item for item in mysql_teacher if item['teacher_id'] == courses[i]['teacher']), None)
            time_slot = next((item for item in local_db_time_slots if item['time'] == courses[i]['time']), None)

            if None in [teacher, course, classroom, campus, time_slot]:
                continue

            result["courses"].append({
                "schedule_id": courses[i]['schedule_id'],
                "course_id": courses[i]['class_id'],
                "classroom_id": courses[i]['classroom'],
                "name": course['class_name'],
                "classroom": classroom['classroom_name'],
                "campus": campus['name'],
                "capacity": classroom['capacity'],
                "time_slot": time_slot['time_slot'],
            })

        return jsonify(result)  # 返回结果到前端

    except Exception as e:
        print('An error occurred while trying to get courses', e)
        return jsonify({"message": "An error occurred while trying to get courses", "data": []}), 500
    
@app.route('/api/teacher/change/time', methods=['POST'])
@cross_origin()
def change_teacher_time():
    local_db_schedule_res, local_db_courses, local_db_campus, local_db_teacher, local_db_classrooms, local_db_time_slots = get_local_db()
    data = request.get_json()
    schedule_id = data.get('schedule_id')
    target_time_slot = data.get('time_slot')

    # 从 time_slots 集合中查找对应的 time
    target_time = next((item['time'] for item in local_db_time_slots if item['time_slot'] == target_time_slot), None)

    if target_time is None:
        return jsonify({"success": False, "message": "Invalid time_slot."}), 400

    try:
        # 获取目标时间对应的所有课程
        target_courses = [item for item in local_db_schedule_res if item['time'] == target_time]

        # 获取这些课程的教室id
        target_classrooms = [course['classroom'] for course in target_courses]

        # 获取所有的教室
        all_classrooms = local_db_classrooms

        # 筛选出在目标时间没有被占用的教室
        available_classrooms = [classroom for classroom in all_classrooms if classroom['classroom_id'] not in target_classrooms]

        # 检查 available_classrooms 是否为空
        if len(available_classrooms) == 0:
            return jsonify({"success": True, "classes": []}), 200

        # 将 available_classrooms 转换为所需的格式
        available_classrooms_new = [{"campus_id": classroom['campus_id'], "capacity": classroom['capacity'], "class_id": classroom['classroom_id'], "classroom_name": classroom['classroom_name'], "equipment": classroom['equipment']} for classroom in available_classrooms]

        return jsonify({"success": True, "classes": available_classrooms_new}), 200
    except Exception as e:
        print('An error occurred while trying to connect to MongoDB', e)
        return jsonify({"message": "An error occurred while trying to connect to MongoDB"}), 500

    
@app.route('/api/teacher/change/class', methods=['POST'])
@cross_origin()
def change_teacher_class():
    data = request.get_json()
    schedule_id = data.get('schedule_id')
    min_capacity = data.get('min_capacity')
    min_equip = data.get('min_equip')

    try:
        local_db_schedule_res, local_db_courses, local_db_campus, local_db_teacher, local_db_classrooms, local_db_time_slots = get_local_db()
        # 查找满足条件的教室
        available_classes = [c for c in local_db_classrooms if c['capacity'] >= min_capacity and all(equip in c['equipment'] for equip in min_equip)]

        # 获取当前课程的时间
        current_schedule = next((item for item in local_db_schedule_res if item['schedule_id'] == schedule_id), None)
        current_time = current_schedule.get('time') if current_schedule else None

        # 检查教室是否在该时间段被其他课程占用
        for c in available_classes[:]:
            classroom_id = c.get('classroom_id')
            if classroom_id is not None:
                classroom_schedule = next((item for item in local_db_schedule_res if item['classroom'] == classroom_id and item['time'] == current_time), None)
                if classroom_schedule is not None:
                    available_classes.remove(c)  # 如果教室在这个时间段被占用，那么从可用教室列表中移除这个教室

        available_classes_new = []
        for c in available_classes:
            new_c = c.copy()  # 创建一个新的字典
            new_c.pop('_id', None)  # 删除 _id 字段
         #   new_c.pop('classroom_name', None)  # 删除 classroom_name 字段
            new_c['class_id'] = new_c.pop('classroom_id', None)  # 将 'classroom_id' 改为 'class_id'
            available_classes_new.append(new_c)

        if len(available_classes_new) == 0:
            return jsonify({"success": True, "classes": []})  # 没有合适的教室
        else:
            return jsonify({"success": True, "classes": available_classes_new})  # 显示可切换的教室
    except Exception as e:
        print('An error occurred while trying to connect to MongoDB', e)
        return jsonify({"message": "An error occurred while trying to connect to MongoDB"}), 500
    
        

@app.route('/api/change/schedule/time', methods=['POST'])
@cross_origin()
def change_schedule_time():
    local_db_schedule_res, local_db_courses, local_db_campus, local_db_teacher, local_db_classrooms, local_db_time_slots = get_local_db()
    data = request.json
    schedule_id = data['schedule_id']
    time_slot_id = data['time_slot']
    classroom_id = data['classroom_id']

    # 从 time_slots 集合中查找对应的时间字符串
    time_slot = next((item['time'] for item in local_db_time_slots if item['time_slot'] == time_slot_id), None)
    if time_slot is None:
        return jsonify(success=False, message="Time slot not found")  # Time slot not found

    try:
        # Check if the classroom is occupied at this time slot
        class_schedule = next((item for item in local_db_schedule_res if item['classroom'] == classroom_id and item['time'] == time_slot), None)
        if class_schedule is not None:
            return jsonify(success=False,message = "Classroom time conflict")  # Classroom time conflict

        # Update the schedule
        schedule = next((item for item in local_db_schedule_res if item['schedule_id'] == schedule_id), None)
        if schedule is not None:
            schedule['time'] = time_slot
            schedule['classroom'] = classroom_id
            schedule_res_collection.update_one({'schedule_id': schedule_id}, {'$set': {'time': time_slot, 'classroom': classroom_id}})  # Update MongoDB
            schedule.pop('_id', None)  # 删除 _id 字段
            return jsonify(success=True)  # Return the modified schedule item
        else:
            return jsonify(success=False, message="Schedule not found")  # Schedule not found
    except Exception as e:
        print('An error occurred while trying to connect to MongoDB', e)
        return jsonify(message='An error occurred while trying to connect to MongoDB'), 500
    

@app.route('/api/change/schedule/classroom', methods=['POST'])
@cross_origin()
def change_schedule_classroom():
    local_db_schedule_res, local_db_courses, local_db_campus, local_db_teacher, local_db_classrooms, local_db_time_slots = get_local_db()
    data = request.get_json()
    schedule_id = data['schedule_id']
    classroom_id = data['classroom_id']

    # 从 classrooms 集合中查找对应的教室
    classroom = next((item for item in local_db_classrooms if item['classroom_id'] == classroom_id), None)
    if classroom is None:
        return jsonify(success=False, message="Classroom not found")  # Classroom not found

    try:
        # Check if the classroom is occupied at this time slot
        class_schedule = next((item for item in local_db_schedule_res if item['classroom'] == classroom['classroom_id'] and item['schedule_id'] == schedule_id), None)
        if class_schedule is not None:
            return jsonify(success=False,message="Classroom time conflict")  # Classroom time conflict

        # Update the schedule
        schedule = next((item for item in local_db_schedule_res if item['schedule_id'] == schedule_id), None)
        if schedule is not None:
            schedule['classroom'] = classroom['classroom_id']
            schedule_res_collection.update_one({'schedule_id': schedule_id}, {'$set': {'classroom': classroom['classroom_id']}})  # Update MongoDB
            schedule.pop('_id', None)  # 删除 _id 字段
            return jsonify(success=True)  # Return the modified schedule item
        else:
            return jsonify(success=False, message="Schedule not found")  # Schedule not found
    except Exception as e:
        print('An error occurred while trying to connect to MongoDB', e)
        return jsonify(message='An error occurred while trying to connect to MongoDB'), 500

@app.route('/api/reschedule', methods=['POST'])
@cross_origin()
def reschedule_classes():
    schedule_interface()
    #schedule_done.set()
    local_db_schedule_res, local_db_courses, local_db_campus, local_db_teacher, local_db_classrooms, local_db_time_slots = get_local_db()
    schedule_res = local_db_schedule_res.copy()  # 使用本地数据

    mysql_courses = get_course_from_mysql()
    mysql_teacher = get_teacher_from_mysql()

    result = {"schedules": []}

    for document in schedule_res:
        course = next((item for item in mysql_courses if item['class_id'] == document['class_id']), None)
        classroom = next((item for item in local_db_classrooms if item['classroom_id'] == document['classroom']), None)
        campus = next((item for item in local_db_campus if item['name'] == course['campus_id']), None) if course else None
        teacher = next((item for item in mysql_teacher if item['teacher_id'] == document['teacher']), None)
        time_slot = next((item for item in local_db_time_slots if item['time'] == document['time']), None)

        if None in [teacher, course, classroom, campus, time_slot]:
            continue

        result["schedules"].append({
            "Schedule_id": document['schedule_id'],
            "teacher": teacher['teacher_name'],
            "time_slot": time_slot['time'],
            "course": course['class_name'],
            "classroom": classroom['classroom_name'],
            "campus": campus['name'],
        })

    # 在新线程中更新 MongoDB
    threading.Thread(target=update_mongodb).start()
    threading.Thread(target=modify_course_list_with_schedule(schedule_res)).start()

    return jsonify(result)


@app.route('/api/schedule', methods=['GET'])
@cross_origin()
def get_schedule():
    local_db_schedule_res, local_db_courses, local_db_campus, local_db_teacher, local_db_classrooms, local_db_time_slots = get_local_db()
    schedule_res = local_db_schedule_res.copy()  # 使用本地数据
    
    result = {"schedules": []}
    mysql_courses = get_course_from_mysql()
    mysql_teacher = get_teacher_from_mysql()

    for document in schedule_res:
        course = next((item for item in mysql_courses if item['class_id'] == document['class_id']), None)
        if course is None:
            print(f"Missing course for class_id: {document['class_id']}")
        classroom = next((item for item in local_db_classrooms if item['classroom_id'] == document['classroom']), None)
        if classroom is None:
            print(f"Missing classroom for classroom_id: {document['classroom']}")
        campus = next((item for item in local_db_campus if item['name'] == course['campus_id']), None) if course else None
        if campus is None:
            print(f"Missing campus for campus_id: {course['campus_id']}")
        teacher = next((item for item in mysql_teacher if item['teacher_id'] == document['teacher']), None)
        if teacher is None:
            print(f"Missing teacher for teacher_id: {document['teacher']}")
        time_slot = next((item for item in local_db_time_slots if item['time'] == document['time']), None)
        if time_slot is None:
            print(f"Missing time_slot for time: {document['time']}")

        if None in [teacher, course, classroom, campus, time_slot]:
            continue

        result["schedules"].append({
            "Schedule_id": document['schedule_id'],
            "teacher": teacher['teacher_name'],
            "time_slot": time_slot['time'],
            "course": course['class_name'],
            "classroom": classroom['classroom_name'],
            "campus": campus['name'],
        })

    return jsonify(result)


if __name__ == '__main__':
    app.run(debug=True)
    
