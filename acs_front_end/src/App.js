import logo from "./logo.svg";
import "./App.css";
import Nav from "./Nav/nav";
import TNav from "./TNav/nav";
import Topbar from "./topbar/topbar";
import Course from "./course/course";
import Classroom from "./classroom/classroom";
import RoomList from "./list/list";
import Login from "./login/login";
import ClassroomCourse from "./course/classroomCourse";
import {
  BrowserRouter as Router,
  Route,
  Routes,
  Navigate
} from "react-router-dom";
import Schedule from "./shedule/schedule";
const NotFound = () => <h1>404</h1>;
function App() {
  return (
    <Router>
      <Routes>
      <Route path="/" element={<Navigate to="/login/" replace />} />
        <Route
          exact
          path="/login/"
          element={
            <div>
              <Topbar />
              <Login></Login>
            </div>
          }
        />
        <Route
          exact
          path="/admin/"
          element={
            <div>
              <Topbar />
              <Nav />
            </div>
          }
        />
        <Route
          exact
          path="/teacher/"
          element={
            <div>
              <Topbar />
              <TNav />
            </div>
          }
        />
        <Route
          exact
          path="/teacher/course/:course_id"
          element={
            <div>
              <Topbar />
              <TNav />
              <Course></Course>
            </div>
          }
        />
        <Route
          exact
          path="/admin/classroom"
          element={
            <div>
              <Topbar />
              <Nav />
              <Classroom></Classroom>
            </div>
          }
        />
        <Route
          exact
          path="/admin/classroom/list"
          element={
            <div>
              <Topbar />
              <Nav />
              <RoomList></RoomList>
            </div>
          }
        />
        <Route
          exact
          path="/admin/classroom/course/:classroom_id"
          element={
            <div>
              <Topbar />
              <Nav />
              <ClassroomCourse></ClassroomCourse>
            </div>
          }
        />
        <Route
          exact
          path="/admin/schedule"
          element={
            <div>
              <Topbar />
              <Nav />
              <Schedule></Schedule>
            </div>
          }
        />

        <Route path="*" element={<NotFound />} />
      </Routes>
    </Router>
  );
}

export default App;
