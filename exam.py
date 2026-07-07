from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from starlette.responses import JSONResponse
from pydantic import BaseModel, Field
from datetime import datetime, timezone
from typing import Optional, Any

app = FastAPI(
    title="Elearning course API",
    description="API hệ thống khóa học trực tuyến"
)

# Tạo khuôn dữ liệu trả về
class APIResponse(BaseModel):
    success: bool
    statusCode: int
    message: str
    data: Optional[Any] = None
    error: Optional[Any] = None
    timestamp: str
    path: str

# Tạo hàm để trả về dữ liệu khi thành công
def success_response(request: Request, status_code: int, message: str, data: Any = None) -> dict:
    return APIResponse(
        success=True,
        statusCode=status_code,
        message=message,
        data=data,
        timestamp=datetime.utcnow().isoformat() + "Z",
        path=request.url.path
    ).model_dump()

# Cơ sở dữ liệu giả lập
courses_db = [
    {"id": 1, "course_name": "FastAPI Masterclass", "duration_hours": 32, "price": 1500000, "status": "active", "created_at": "2026-07-01T02:00:00Z"},
    {"id": 2, "course_name": "NextJS Next-Level", "duration_hours": 45, "price": 1800000, "status": "active", "created_at": "2026-07-01T03:15:00Z"}
]

class CourseCreate(BaseModel):
    course_name: str = Field(..., min_length=5)
    duration_hours: int = Field(..., gt=0)
    price: int = Field(..., ge=0)

@app.exception_handler(RequestValidationError)
def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content=APIResponse(
            success=False,
            statusCode=422,
            message="Lỗi: Dữ liệu đầu vào không hợp lệ!",
            error=exc.errors(),
            timestamp=datetime.utcnow().isoformat() + "Z",
            path=request.url.path
        ).model_dump()
    )

@app.exception_handler(HTTPException)
def http_exception_handler(request: Request, exc: HTTPException):
    detail = exc.detail
    message = "Yêu cầu không hợp lệ"
    error_code = None
    
    if isinstance(detail, dict):
        message = detail.get("message", message)
        error_code = detail.get("error", None)
    else:
        message = str(detail)
        error_code = str(detail)

    return JSONResponse(
        status_code=exc.status_code,
        content=APIResponse(
            success=False,
            statusCode=exc.status_code,
            message=message,
            error=error_code,
            timestamp=datetime.utcnow().isoformat() + "Z",
            path=request.url.path
        ).model_dump()
    )

@app.exception_handler(Exception)
def global_exception_handler(request: Request, exc: Exception):
    # Ghi log lỗi để dev kiểm tra, nhưng giấu lỗi thật khỏi người dùng để bảo mật
    return JSONResponse(
        status_code=500,
        content=APIResponse(
            success=False,
            statusCode=500,
            message="Đã xảy ra lỗi hệ thống. Vui lòng liên hệ quản trị viên.",
            error=str(exc),
            timestamp=datetime.utcnow().isoformat() + "Z",
            path=request.url.path
        ).model_dump()
    )

# 1. API: Lấy danh sách khóa học
@app.get("/courses", response_model=APIResponse)
def get_courses(request: Request):
    return success_response(request, 200, "Lấy danh sách khóa học thành công!", courses_db)

# 2. API: Tạo mới một khóa học
@app.post("/courses", status_code=201, response_model=APIResponse)
def create_course(request: Request, course_data: CourseCreate):
    # Kiểm tra trùng tên bằng vòng lặp for thông thường
    name_exists = False
    for c in courses_db:
        if c["course_name"] == course_data.course_name:
            name_exists = True
            break
            
    if name_exists:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Lỗi: Tên khóa học này đã tồn tại trong danh mục đào tạo!",
                "error": "ERR-EDU-01: Course name duplicates an existing record in memory array."
            }
        )
    
    # Tìm ID lớn nhất bằng cách duyệt qua danh sách
    max_id = 0
    for c in courses_db:
        if c["id"] > max_id:
            max_id = c["id"]
    new_id = max_id + 1
    
    new_course = {
        "id": new_id,
        "course_name": course_data.course_name,
        "duration_hours": course_data.duration_hours,
        "price": course_data.price,
        "status": "active",
        "created_at": datetime.utcnow().isoformat() + "Z"
    }
    courses_db.append(new_course)
    
    return success_response(request, 201, "Tạo mới khóa học thành công!", new_course)

# 3. API: Xóa bỏ một khóa học
@app.delete("/courses/{course_id}", response_model=APIResponse)
def delete_course(request: Request, course_id: int):
    # Tìm vị trí (chỉ số index) của khóa học cần xóa
    target_idx = -1
    for idx in range(len(courses_db)):
        if courses_db[idx]["id"] == course_id:
            target_idx = idx
            break
            
    if target_idx == -1:
        raise HTTPException(
            status_code=404,
            detail={
                "message": "Lỗi: Không tìm thấy mã khóa học yêu cầu để xóa!",
                "error": "ERR-EDU-02: Target course ID can not be found."
            }
        )
        
    courses_db.pop(target_idx)
    
    return success_response(request, 200, "Xóa khóa học thành công!")
