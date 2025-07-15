<script>
  import { onMount } from 'svelte';
  
  let name = 'Medveda'

  // Authentication state
  let isAuthenticated = false;
  let username = '';
  let password = '';
  let loginError = '';
  
  // Dashboard state
  let sqlQuery = '';
  let queryResults = [];
  let columns = [];
  let loading = false;
  let error = '';
  
  // Table filtering and sorting
  let filterText = '';
  let sortColumn = '';
  let sortDirection = 'asc';
  
  // Mock authentication - replace with real authentication
  const authenticate = async () => {
    if (username === 'admin' && password === 'password') {
      isAuthenticated = true;
      loginError = '';
    } else {
      loginError = 'Invalid credentials';
    }
  };
  
  const logout = () => {
    isAuthenticated = false;
    username = '';
    password = '';
    sqlQuery = '';
    queryResults = [];
    columns = [];
  };
  
  // Mock SQL query execution - replace with actual database connection
  const executeQuery = async () => {
    if (!sqlQuery.trim()) {
      error = 'Please enter a SQL query';
      return;
    }
    
    loading = true;
    error = '';
    
    try {

      var response = await fetch('http://localhost:5000/mock.json', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: sqlQuery.trim(),
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      queryResults = await response.json();
      columns = Object.keys(queryResults[0])
    } catch (err) {
      error = 'Error executing query: ' + err.message;
    } finally {
      loading = false;
    }
  };
  
  // Filtering and sorting logic
  $: filteredResults = queryResults.filter(row => {
    if (!filterText) return true;
    return Object.values(row).some(value => 
      String(value).toLowerCase().includes(filterText.toLowerCase())
    );
  });
  
  $: sortedResults = [...filteredResults].sort((a, b) => {
    if (!sortColumn) return 0;
    
    const aVal = a[sortColumn];
    const bVal = b[sortColumn];
    
    if (aVal < bVal) return sortDirection === 'asc' ? -1 : 1;
    if (aVal > bVal) return sortDirection === 'asc' ? 1 : -1;
    return 0;
  });
  
  const handleSort = (column) => {
    if (sortColumn === column) {
      sortDirection = sortDirection === 'asc' ? 'desc' : 'asc';
    } else {
      sortColumn = column;
      sortDirection = 'asc';
    }
  };
  
  const handleKeyPress = (event) => {
    if (event.key === 'Enter') {
      if (!isAuthenticated) {
        authenticate();
      } else {
        executeQuery();
      }
    }
  };
</script>

<main class="container">
  {#if !isAuthenticated}
    <!-- Login Form -->
    <div class="login-container">
      <div class="login-form">
        <h2>{name}</h2>
        <form on:submit|preventDefault={authenticate}>
          <div class="form-group">
            <label for="username">Username:</label>
            <input
              type="text"
              id="username"
              bind:value={username}
              on:keypress={handleKeyPress}
              required
            />
          </div>
          <div class="form-group">
            <label for="password">Password:</label>
            <input
              type="password"
              id="password"
              bind:value={password}
              on:keypress={handleKeyPress}
              required
            />
          </div>
          {#if loginError}
            <div class="error">{loginError}</div>
          {/if}
          <button type="submit" class="login-btn">Login</button>
        </form>
        <!--div class="demo-info">
          <p><strong>Demo credentials:</strong></p>
          <p>Username: admin</p>
          <p>Password: password</p>
        </div-->
      </div>
    </div>
  {:else}
    <!-- Dashboard -->
    <div class="dashboard">
      <header class="dashboard-header">
        <h1>{name}</h1>
        <div class="user-info">
          <span>Welcome, {username}</span>
          <button on:click={logout} class="logout-btn">Logout</button>
        </div>
      </header>
      
      <div class="query-section">
        <div class="query-box">
          <label for="sqlQuery">Describe the data to retrieve:</label>
          <textarea
            id="sqlQuery"
            bind:value={sqlQuery}
            placeholder="How many records are there?"
            rows="5"
          ></textarea>
          <button on:click={executeQuery} disabled={loading} class="execute-btn">
            {loading ? 'Executing...' : 'Execute Query'}
          </button>
        </div>
        
        {#if error}
          <div class="error">{error}</div>
        {/if}
      </div>
      
      {#if queryResults.length > 0}
        <div class="results-section">
          <div class="results-header">
            <h3>Query Results ({queryResults.length} rows)</h3>
            <div class="filter-box">
              <label for="filter">Filter:</label>
              <input
                type="text"
                id="filter"
                bind:value={filterText}
                placeholder="Filter results..."
              />
            </div>
          </div>
          
          <div class="table-container">
            <table class="results-table">
              <thead>
                <tr>
                  {#each columns as column}
                    <th on:click={() => handleSort(column)} class="sortable">
                      {column}
                      {#if sortColumn === column}
                        <span class="sort-indicator">
                          {sortDirection === 'asc' ? '▲' : '▼'}
                        </span>
                      {/if}
                    </th>
                  {/each}
                </tr>
              </thead>
              <tbody>
                {#each sortedResults as row}
                  <tr>
                    {#each columns as column}
                      <td>{row[column]}</td>
                    {/each}
                  </tr>
                {/each}
              </tbody>
            </table>
          </div>
          
          <div class="results-info">
            Showing {sortedResults.length} of {queryResults.length} results
          </div>
        </div>
      {/if}
    </div>
  {/if}
</main>
