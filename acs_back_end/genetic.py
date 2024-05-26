import numpy as np
import argparse
import random
import pymongo
import utils
from database import get_local_db, update_local_db
from threading import Event
import copy

schedule_done = Event()

def get_num(ss):
    a = ss//10
    b = ss%10
    return int((a-1)*5 + b-1)

def euclidean_distance(a, b):
    return np.linalg.norm(a - b)

def normalized_euclidean_distance(a, b):
    distance = euclidean_distance(a, b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    max_norm = max(norm_a, norm_b)
    return distance / max_norm

def check_collision(ind,dict):
    res = True
    for i in dict.keys():
        list = []
        for j in dict[i]:
            list.append(ind[j])
        if len(list) != len(set(list)):
            res = False
            break
    return res

def fitness(individual,num_courses,num_timeslots,tc_dict):
    num = num_courses//num_timeslots
    array = np.full(num_timeslots, num)
    temp = np.zeros(num_timeslots)
    for i in individual:
        temp[get_num(i)] += 1
    dot_product = np.dot(array, temp)
    norm_a = np.linalg.norm(array)
    norm_b = np.linalg.norm(temp)
    if check_collision(individual,tc_dict):
        return dot_product / (norm_a * norm_b)
    else:
        return (dot_product / (norm_a * norm_b))/2
    # return dot_product / (norm_a * norm_b)

def get_answer(population,num_courses,num_timeslots,num_rooms,population_size,generations,mutation_rate,tc_dict):
    class_time = np.array([11, 12, 13, 14, 15,
                           21, 22, 23, 24, 25,
                           31, 32, 33, 34, 35,
                           41, 42, 43, 44, 45,
                           51, 52, 53, 54, 55])
    for generation in range(generations):
        # 计算适应度
        fitnesses = np.array([fitness(ind,num_courses,num_timeslots,tc_dict) for ind in population])

        # 选择操作（这里使用简单的轮盘赌选择）
        selected_indices = np.random.choice(range(population_size), size=population_size, replace=True,
                                            p=fitnesses / fitnesses.sum())
        selected_population = []
        for i in selected_indices:
            selected_population.append(population[i])
        # 交叉和变异
        new_population = []
        for i in range(0, population_size, 2):
            parent1, parent2 = selected_population[i], selected_population[i + 1]
            # 交叉操作
            crossover_point = np.random.randint(0, num_courses)
            child1 = np.concatenate([parent1[:crossover_point], parent2[crossover_point:]])
            child2 = np.concatenate([parent2[:crossover_point], parent1[crossover_point:]])
            # 变异操作

            if np.random.rand() < mutation_rate:
                mutation_point = np.random.randint(0, num_courses)
                child1[mutation_point] = class_time[np.random.randint(0, num_timeslots)]
            if np.random.rand() < mutation_rate:
                mutation_point = np.random.randint(0, num_courses)
                child2[mutation_point] = class_time[np.random.randint(0, num_timeslots)]
            new_population.append(child1)
            new_population.append(child2)

        population = np.array(new_population)

    final_fitnesses = np.array([fitness(ind,num_courses,num_timeslots,tc_dict) for ind in population])
    best_index = np.argmax(final_fitnesses)
    best_solution = population[best_index]
    return final_fitnesses[best_index],best_solution
    # print("最优解的适应度:", final_fitnesses[best_index])
    # print("最优排课方案:\n", best_solution)
    #
    # temp = np.zeros(num_timeslots)
    # for i in best_solution:
    #     temp[get_num(i)] += 1
    # print(temp)

def get_time(k):
    day = k//10
    slot = k%10
    d1 = {
        1:"周一",
        2:"周二",
        3:"周三",
        4:"周四",
        5:"周五",
    }
    d2 = {
        1:"8:00-9:30",
        2:"10:00-11:30",
        3:"14:00-15:30",
        4:"16:00-17:30",
        5:"19:00-20:30"
    }
    return d1[day] + d2[slot]

def init(dict,num_courses,class_time,num_timeslots):
    id = random.randint(0,num_timeslots)
    res = np.zeros(num_courses)
    for i in dict.keys():
        random_integers = random.sample(range(num_timeslots), len(dict[i]))
        index = 0
        for j in dict[i]:
            res[j] = class_time[random_integers[index]]
            index += 1
    print(res)
    return res

def schedule_course(num_courses,num_rooms,cids,tids,classroom_ids):
    # 初始化种群
    mutation_rate = 0.01
    num_timeslots = 25
    population_size = 100
    generations = 10
    teacher_num = 20
    class_time = np.array([11, 12, 13, 14, 15,
                           21, 22, 23, 24, 25,
                           31, 32, 33, 34, 35,
                           41, 42, 43, 44, 45,
                           51, 52, 53, 54, 55])

    per_teacher_course = num_courses//teacher_num
    tc_dict = {}
    for i in range(0, num_courses):
        tid = tids[i]
        cid = cids[i]
        if tid in tc_dict:
            tc_dict[tid].append(cid)
        else:
            l = []
            l.append(cid)
            tc_dict[tid] = l




    # id = 0
    # for i in range(0,teacher_num):
    #     list = []
    #     for j in range(0,per_teacher_course):
    #         list.append(id)
    #         id += 1
    #     tc_dict[i] = list

    population = [init(tc_dict,num_courses,class_time,num_timeslots) for _ in range(population_size)]
    best_score = 0
    best_solution = np.zeros(num_courses)
    for i in range(0,1):
        score,solution = get_answer(population,num_courses,num_timeslots,num_rooms,population_size,generations,mutation_rate,tc_dict)
        if score>best_score:
            best_score = score
            best_solution = solution
    print("最优解的适应度:", best_score)
    print("best_solution:",fitness(best_solution,num_courses,num_timeslots,tc_dict))
    print("最优排课方案:\n", best_solution)
    dict = {}
    for i in range(0,num_courses):
        if int(best_solution[i]) in dict.keys():
            dict[int(best_solution[i])].append(i)
        else:
            list = []
            list.append(i)
            dict[int(best_solution[i])] = list
    print(dict)
    classroom_res = np.zeros(num_courses)
    for i in range(0,num_timeslots):
        room_id = 0
        if class_time[i] not in dict:
            continue
        for j in dict[class_time[i]]:
            classroom_res[j] = classroom_ids[room_id]
            room_id += 1
    schedule_ids = []
    class_ids = []
    times = []
    classrooms = []
    teachers = []
    for i in range(0,num_courses):
        schedule_ids.append(i)
        class_ids.append(i)
        times.append(get_time(best_solution[i]))
        classrooms.append(int(classroom_res[i]))
        teachers.append(tids[i])
    for i in range(0, num_courses):
        print("class:", i, " time:", get_time(best_solution[i]), " classroom:room", int(classroom_res[i])," teacher:",teachers[i])
    print("最优解的适应度:", best_score)
    temp = np.zeros(num_timeslots)
    for i in best_solution:
        temp[get_num(i)] += 1
    print(temp)
    print("res:",check_collision(best_solution,tc_dict))
    return schedule_ids,class_ids,times,classrooms,teachers

def prepare_info():
    number = 100
    cids = []
    names = utils.names
    teachers = []
    campus = []
    for i in range(0,100):
        cids.append(i)
        teachers.append(random.randint(0, 39)%40)
        if random.randint(0, 10)>5:
            campus.append("紫金港")
        else:
            campus.append("玉泉")
    return cids,names,teachers,campus



def schedule_interface():
    # 获取本地数据库
    local_db_schedule_res, local_db_courses, local_db_campus, local_db_teacher, local_db_classrooms, local_db_time_slots = get_local_db()

    # 从本地数据库中获取课程和教室信息
    courses = copy.deepcopy(local_db_courses)
    classrooms = copy.deepcopy(local_db_classrooms)
    cid = []
    tid = []
    for doc in courses:
        tid.append(doc["teacher_id"])
        cid.append(doc["class_id"])
    course_num = len(courses)
    classroom_num = len(classrooms)



    classroom_ids = []
    for doc in classrooms:
        classroom_ids.append(doc["classroom_id"])
    print(classroom_ids)
    schedule_ids,class_ids,times,classrooms,teachers = schedule_course(course_num,classroom_num,cid,tid,classroom_ids)





    # schedule_ids, class_ids, times, classrooms, teachers = schedule_course(course_num, classroom_num, cid, tid)

    data = []
    for i in range(0, course_num):
        item = {}
        item["schedule_id"] = schedule_ids[i]
        item["class_id"] = class_ids[i]
        item["time"] = times[i]
        item["classroom"] = classrooms[i]
        item["teacher"] = teachers[i]
        data.append(item)

    print(data)

    # 更新本地数据库
    update_local_db(data, local_db_courses, local_db_campus, local_db_teacher, local_db_classrooms, local_db_time_slots)
    schedule_done.set()


    # 打印所有表名
    # collections = mydb.list_collection_names()
    # for collection in collections:
    #     print(collection)
    # # 打印已插入数据

    # for doc in mycollection.find():
    #     print(doc)
if __name__ == '__main__':
    schedule_interface()