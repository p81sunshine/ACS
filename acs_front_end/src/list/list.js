import React from "react";
import axios from "axios";
import { useState, useEffect } from "react";
import { Modal, Form, Input, Button, message, Space, Table, Tag, Select } from "antd";
const { Option } = Select;
export default function RoomList() {
  const columns = [
    {
      title: "教室名称",
      dataIndex: "name",
      key: "classroomName",
    },
    {
      title: "校区",
      dataIndex: "campus",
      key: "campus",
    },
    {
      title: "容量",
      dataIndex: "capacity",
      key: "capacity",
    },
    {
      title: "设备",
      key: "equipment",
      dataIndex: "equipment",
    },
    {
      title: "Action",
      key: "action",
      render: (_, record) => (
        <Space size="middle">
          <a onClick={() => handleDelete(record.id)}>删除</a>
          <a onClick={() => handleModify(record)}>修改</a>
        </Space>
      ),
    },
  ];

  const id2campus = [
    "紫金港",
    "玉泉",
    "西溪",
    "华家池",
    "之江",
    "舟山",
    "海宁"
  ]

  const compus2id = {
    "紫金港":0,
    "玉泉":1,
    "西溪":2,
    "华家池":3,
    "之江":4,
    "舟山":5,
    "海宁":6
  }

  const [classData, setClassData] = useState([]);
  const [selectedRecord, setSelectedRecord] = useState(null);  
  const [isModalVisible, setIsModalVisible] = useState(false);


  const handleModify = (record) => {  
    console.log('record', record)
    setSelectedRecord(record);  
    setFormData({
      record_id: record.id,
      classroomName: record.name,
      campus: record.campus,
      capacity: record.capacity,
      equipment: record.equipment.split(", "),
    });
    console.log('fromdata', formData)
    setIsModalVisible(true);  
  };  
  
  const handleModalCancel = () => {  
    setIsModalVisible(false);  
  };  
  
  const handleModalOk = () => {  
    // Logic to handle the modification, e.g., making an API call to update the record  
    setIsModalVisible(false);  
    
  }; 

  const [formData, setFormData] = useState({  
    record_id: 1000000,
    classroomName: '',  
    campus: '',  
    capacity: '',  
    equipment: []  
  })

  const handleFormChange = (changedValues, allValues) => {  
    setFormData(allValues);  
  };

  const onFinish = async (values) => {  
    try {  
      const body = {
        "classroom_id": values.record_id,
        "classroom_name": values.classroomName,
        "campus": values.campus,
        "equipment": values.equipment,
        "capacity": Number(values.capacity),

      }
      console.log('Put body',body)
      const response = await axios.put(`http://127.0.0.1:5000/api/classrooms/${values['record_id']}`, body);  
      console.log(response)
      message.success("success")
    } catch (error) { 
      console.log(error) 
      message.error("error")
    }  
  };  
  
  const onFinishFailed = (errorInfo) => {  
    message.error('请填写必填项')  
  }; 

  const fetchData = async () => {
    try {
      const res = await axios.get("http://127.0.0.1:5000/api/classrooms");
      const mappedData = res.data.map(item=>{
        return{campus: id2campus[item.campus_id],  
          capacity: item.capacity,  
          equipment: item.equipment,  
          id: item.id,  
          name: item.name }})
      setClassData(mappedData);
      console.log(mappedData);
    } catch (error) {
      console.log(error);
    }
  };

  const handleDelete = async (key) => {
    try {
      const res = await axios.delete(
        `http://127.0.0.1:5000/api/classrooms/${key}`
      );
      if (res.status === 200) {
        message.success("删除成功");
      }
      console.log(res.data);
      // After deleting, fetch the data again to update the list
      fetchData();
    } catch (error) {
      console.log(error);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  return (
    <div>
      <div style={{ marginLeft: "15vw" }}>
        <Table columns={columns} dataSource={classData} />
        <Modal  
          title="修改记录"  
          visible={isModalVisible}  
          onOk={handleModalOk}  
          onCancel={handleModalCancel}  
          footer={null}
        >  
          {/* Form to modify the selected record */}  
          {selectedRecord && (  
            <Form  
              name="inputForm"  
              initialValues={formData}  // 使用初始值来填充表单  
              onFinish={onFinish}  
              onFinishFailed={onFinishFailed}  
              onValuesChange={handleFormChange}  // 监听表单值的变化  
              className="input-form"  
            >   
              <Form.Item  
                name="record_id"  
                noStyle  // 不显示该表单项
              ></Form.Item>
              <Form.Item  
                label="教室名"  
                name="classroomName"  
                rules={[{ required: true, message: '请输入教室名' }]}  
              >  
                <Input />  
              </Form.Item>  
          
              <Form.Item  
                label="校区"  
                name="campus"  
                rules={[{ required: true, message: '请选择校区' }]}  
              >  
                <Select>  
                  <Option value="紫金港">紫金港</Option>  
                  <Option value="玉泉">玉泉</Option>  
                  <Option value="西溪">西溪</Option>  
                  <Option value="华家池">华家池</Option>  
                  <Option value="之江">之江</Option> 
                  <Option value="舟山">舟山</Option> 
                  <Option value="海宁">海宁</Option> 
                </Select>  
              </Form.Item> 
          
              <Form.Item  
                label="教室容量"  
                name="capacity"  
                rules={[{ required: true, message: '请输入教室容量' }]}  
              >  
                <Input type="number" />  
              </Form.Item>  
          
              <Form.Item  
                label="教室设备"  
                name="equipment"  
                rules={[{ required: false, message: '请选择教室设备' }]}  
              >  
                <Select mode="multiple">  
                  <Option value="投影仪">投影仪</Option>  
                  <Option value="白板">白板</Option>  
                  <Option value="黑板">黑板</Option>
                  <Option value="激光笔">激光笔</Option>  
                  <Option value="电脑">电脑</Option>  
                  <Option value="fpga开发板">fpga开发板</Option>  
                  <Option value="实验台">实验台</Option>  
                </Select>  
              </Form.Item>   

              <Form.Item className="align-right">  
                  <Button type="primary" htmlType="submit" className='confirm'>  
                    确认  
                  </Button>  
                  <Button type="default" htmlType="button" className="cancel-button" onClick={handleModalCancel}>  
                    取消
                  </Button>    
              </Form.Item>
            </Form>  
          )}  
        </Modal>
      </div>
    </div>
  );
}
