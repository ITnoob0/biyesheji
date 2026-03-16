<template>
  <el-card class="achievement-entry-card" header="Achievement Entry">
    <el-form
      ref="formRef"
      :model="form"
      :rules="rules"
      label-width="120px"
      class="achievement-entry-form"
    >
      <el-form-item label="Paper Title" prop="title">
        <el-input v-model="form.title" placeholder="Enter paper title" />
      </el-form-item>

      <el-form-item label="Abstract" prop="abstract">
        <el-input
          type="textarea"
          v-model="form.abstract"
          :rows="4"
          placeholder="Detailed abstracts help backend AI extract accurate keywords"
        />
      </el-form-item>

      <el-form-item label="Date Acquired" prop="date_acquired">
        <el-date-picker
          v-model="form.date_acquired"
          type="date"
          value-format="YYYY-MM-DD"
          placeholder="Select date"
        />
      </el-form-item>

      <el-form-item label="DOI">
        <el-input v-model="form.doi" placeholder="Enter DOI (optional)" />
      </el-form-item>

      <el-form-item label="Co-authors">
        <el-input
          v-model="form.coauthors"
          placeholder="Enter co-authors (comma separated)"
        />
      </el-form-item>

      <el-form-item label="Paper Type" prop="paper_type">
        <el-select v-model="form.paper_type" placeholder="Select paper type">
          <el-option label="期刊论文" value="journal"></el-option>
          <el-option label="会议论文" value="conference"></el-option>
        </el-select>
      </el-form-item>

      <el-form-item v-if="isAdmin" label="Teacher" prop="teacher">
        <el-autocomplete
          v-model="teacherSearch"
          :fetch-suggestions="querySearchTeacher"
          placeholder="输入教师姓名搜索"
          @select="handleTeacherSelect"
          clearable
        />
      </el-form-item>
      <el-form-item v-else label="Teacher" prop="teacher">
        <el-input v-model="form.teacher" readonly />
      </el-form-item>

      <el-form-item>
        <el-button
          type="primary"
          :loading="loading"
          @click="submitForm"
        >
          Submit
        </el-button>
        <el-button @click="resetForm" :disabled="loading">Reset</el-button>
      </el-form-item>
    </el-form>
  </el-card>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'

const formRef = ref()
const loading = ref(false)
const isAdmin = ref(false)
const teacherSearch = ref('')

onMounted(() => {
  // 假设localStorage有user_id和is_admin
  const userId = localStorage.getItem('user_id')
  form.teacher = userId ? Number(userId) : ''
  isAdmin.value = localStorage.getItem('is_admin') === 'true'
})

const form = reactive({
  title: '',
  abstract: '',
  date_acquired: '',
  doi: '',
  coauthors: '',
  paper_type: '',
  journal_name: '',
  teacher: '',
})

const rules = reactive({
  title: [
    { required: true, message: 'Paper title is required', trigger: 'blur' }
  ],
  abstract: [
    { required: true, message: 'Abstract is required', trigger: 'blur' }
  ],
  date_acquired: [
    { required: true, message: 'Date acquired is required', trigger: 'change' }
  ],
  paper_type: [
    { required: true, message: 'Paper type is required', trigger: 'change' }
  ],
  journal_name: [
    { required: true, message: 'Journal name is required', trigger: 'blur' }
  ],
  teacher: [
    { required: true, message: 'Teacher is required', trigger: 'blur' }
  ],
})

const submitForm = () => {
  if (!formRef.value) return
  formRef.value.validate(async (valid: boolean) => {
    if (!valid) return
    loading.value = true
    try {
      // 构造 payload，coauthors 以逗号分隔字符串传递
      const payload = {
        title: form.title,
        abstract: form.abstract,
        date_acquired: form.date_acquired,
        doi: form.doi || undefined,
        coauthors: form.coauthors
          ? form.coauthors.split(',').map(s => s.trim()).filter(Boolean)
          : [],
        paper_type: form.paper_type,
        journal_name: form.journal_name,
        teacher: form.teacher,
      }
      await axios.post('/api/achievements/papers/', payload)
      ElMessage.success('Submission successful. AI analysis and graph construction in progress in the background.')
      resetForm()
    } catch (err: any) {
      ElMessage.error(
        err?.response?.data?.detail ||
        err?.message ||
        'Submission failed. Please check your input or network.'
      )
    } finally {
      loading.value = false
    }
  })
}

const resetForm = () => {
  if (!formRef.value) return
  formRef.value.resetFields()
}

// 管理员用姓名查找用户ID
const querySearchTeacher = async (queryString: string, cb: Function) => {
  if (!queryString) return cb([])
  try {
    const res = await axios.get(`/api/users/?search=${encodeURIComponent(queryString)}`)
    // 假设返回 [{id: 1, name: '张三'}, ...]
    cb(res.data.map((u: any) => ({ value: u.name, id: u.id })))
  } catch {
    cb([])
  }
}
const handleTeacherSelect = (item: any) => {
  form.teacher = item.id
}
</script>

<style scoped>
.achievement-entry-card {
  max-width: 600px;
  margin: 40px auto;
  --el-card-padding: 32px;
}
.achievement-entry-form {
  margin-top: 16px;
}
</style>
