const apiKey = "b6e2db55b3138e4aedf485a0e7fc82d5"; // Your OpenWeatherMap API key

async function checkWeather() {
    const city = document.getElementById("cityInput").value;
    const resultDiv = document.getElementById("weatherResult");

    if (!city) {
        resultDiv.innerText = "Please enter a city name.";
        return;
    }

    // Construct the API URL
    const url = `https://api.openweathermap.org/data/2.5/weather?q=${city}&units=metric&appid=${apiKey}`;

    try {
        const response = await fetch(url);
        const data = await response.json();

        if (data.cod === 200) {
            resultDiv.innerHTML = `
                <p><strong>${data.name}</strong></p>
                <p>${data.weather[0].description}</p>
                <p>Temperature: ${data.main.temp}°C</p>
                <p>Humidity: ${data.main.humidity}%</p>
            `;
        } else {
            resultDiv.innerText = "City not found.";
        }
    } catch (error) {
        resultDiv.innerText = "Error fetching weather.";
        console.error(error);
    }
}