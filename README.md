# RN-able 2
Django project supporting informatics analyses

Written by Ryland Bednarek

# Setup Instructions

## Installation

### 1. Clone Repository
```bash
git clone https://github.com/rbednarek/rnable.git
cd rnable
```

### 2. Setup
```bash
make setup-all
```

# Running RN-able 2
```bash
conda activate rnable
make run

http://127.0.0.1:8000/
```

To Do:
 - Remove session.count_data = None from de_analysis views once we decide to keep raw count data for session
 - Consider swapping native filename rendering to custom to create space between choose file button and filename
 - Add custom legend to plotly that can be added as CSS variable to bottom of container, extending container. that way we can keep plot same size and have better control over more complex metadata (ie timecourse + treatment group)
 - Check metadata parsing function, do i already concatenate all columns to account for all possible conditions?
 - Consider switching DESeq2 biocmanager install over to conda, currently runs slowly
 - Auth app implementation
 - Enrichment app development
