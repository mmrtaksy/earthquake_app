function fetchEarthquakeData() {
    // JSON yanıtında next_earthquake'ı alın

    $('#fetch-data').text('Yükleniyor');
    $.getJSON('/earthquake_data', function (data) {

        if (data.error) {
            $('#result').text(data.error);
            return;
        }

        if(timer){
            clearInterval(timer);
        }

        timer = setInterval(function () {
            const now = moment();
            const nextEarthquake = moment(data.next_earthquake);
        
            // Kalan süreyi hesapla
            const duration = moment.duration(nextEarthquake.diff(now));
        
            // Gün, saat, dakika ve saniye olarak formatla
            const days = Math.floor(duration.asDays());
            const hours = duration.hours();
            const minutes = duration.minutes();
            const seconds = duration.seconds();
        
            // Ekrana yazdır
            $('#timer').text(`${days} gün ${hours} saat ${minutes} dakika ${seconds} saniye`);
            
            // Deprem zamanı geçmişse sayacı durdur
            if (duration.asMilliseconds() <= 0) {
                clearInterval(timer);
                $('#timer').text("Deprem zamanı geçti.");
            }
        }, 1000);

        $('#result').html(`
            <table class="table table-bordered mt-4">
                <thead>
                    <tr>
                        <th>Veri</th>
                        <th>Değer</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>Ortalama Büyüklük (Mag)</td>
                        <td>${data.average_magnitude.toFixed(2)}</td>
                    </tr>
                    <tr>
                        <td>Bir Sonraki Deprem</td>
                        <td>${moment(data.next_earthquake).format('DD.MM.YYYY HH:mm:ss')}</td>
                    </tr>
                    <tr>
                        <td>Derinlik (km)</td>
                        <td>${data.earthquake_depth}</td>
                    </tr>
                    <tr>
                        <td>Depremin Yeri</td>
                        <td>${data.earthquake_location}</td>
                    </tr>
                    <tr>
                        <td>Büyüklük (Mag)</td>
                        <td>${data.earthquake_magnitude}</td>
                    </tr>
                    <tr>
                        <td>Son Aktif Deprem Sayısı</td>
                        <td>${data.recent_earthquake_count}</td>
                    </tr>
                    <tr>
                        <td>Son Güncelleme</td>
                        <td>${moment(data.last_update).format('DD.MM.YYYY HH:mm:ss')}</td>
                    </tr>
                    <tr>
                        <td>Bugün Tarihi</td>
                        <td>${moment(data.today_date).format('DD.MM.YYYY HH:mm:ss')}</td>
                    </tr>
                </tbody>
            </table>
        `);

        const closestCitiesTable = $('#closestCitiesTable');
        closestCitiesTable.html("");
        data.closest_cities.forEach(city => {
            const row = $(`
                <tr>
                    <td>${city.name}</td>
                    <td>${city.cityCode}</td>
                    <td>${city.distance.toFixed(2)} m</td>
                    <td>${city.population}</td>
                </tr>
            `);


            closestCitiesTable.append(row);
        });


        $('#fetch-data').text('Verileri Getir');
    });

}

// İlk veriyi çek ve belirli aralıklarla güncelle
fetchEarthquakeData();
setInterval(fetchEarthquakeData, 60000); // 60 saniyede bir güncelle


$(document).ready(function () {
    $('#fetch-data').click(function () {
        fetchEarthquakeData();
    });
});
