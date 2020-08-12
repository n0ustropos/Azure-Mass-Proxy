# Azure Mass Proxy 

<!--
*** Thanks for checking out this README Template. If you have a suggestion that would
*** make this better, please fork the repo and create a pull request or simply open
*** an issue with the tag "enhancement".
*** Thanks again! Now go create something AMAZING! :D
***
***
***
*** To avoid retyping too much info. Do a search and replace for the following:
*** github_username, repo, twitter_handle, email
-->





<!-- PROJECT SHIELDS -->
<!--
*** I'm using markdown "reference style" links for readability.
*** Reference links are enclosed in brackets [ ] instead of parentheses ( ).
*** See the bottom of this document for the declaration of the reference variables
*** for contributors-url, forks-url, etc. This is an optional, concise syntax you may use.
*** https://www.markdownguide.org/basic-syntax/#reference-style-links
-->


<!-- PROJECT LOGO -->
<br />
<p align="center">

  <h3 align="center">Azure Mass Proxy</h3>

  <p align="center">
    Easly deploy scaleSets with Squid Proxy on Azure platform
  </p>
</p>



<!-- TABLE OF CONTENTS -->
## Table of Contents

* [About the Project](#about-the-project)
  * [Built With](#built-with)
* [Getting Started](#getting-started)
  * [Installation](#installation)
* [Usage](#usage)
* [License](#license)
* [Contact](#contact)



<!-- ABOUT THE PROJECT -->
## About The Project

Python script created for easy deploying thousands of proxies.


### Built With

* Azure REST API
* Python3
* Cloud-init
* Squid3



<!-- GETTING STARTED -->
## Getting Started



### Installation
 
1. Clone the repo
```sh
git clone https://github.com/n0ustropos/Azure-Mass-Proxy
```
2. Install packages
```sh
pip3 install adal
pip3 install pandas
```



<!-- USAGE EXAMPLES -->
## Usage

* Get Azure account with proper subscriptions
* Add your own credentials to configs/azureConfig.conf
* Change all login/pass credentials in azure.py and cloudinit.yaml for your own
* Configure Squid3 in cloudinit.yaml
* Configure scaleSet settings in azure.py
* Run 
```
python3 azure.py
```
* Check limits by choosing option 3
* Set your desired number of proxies in configs/azureConfig.conf, minding the limits
* Run azure.py again, this time choose option 0 for deployment
* After successful deployment, run azure.py and reboot all scaleSets with option 4
* Fetch all proxy IPs using option 1, which will be saved to proxyOutput.xlsx




<!-- LICENSE -->
## License

Distributed under the MIT License. See `LICENSE` for more information.



<!-- CONTACT -->
## Contact

Project Link: [https://github.com/n0ustropos/Azure-Mass-Proxy](https://github.com/n0ustropos/Azure-Mass-Proxy)





<!-- MARKDOWN LINKS & IMAGES -->
<!-- https://www.markdownguide.org/basic-syntax/#reference-style-links -->
[contributors-shield]: https://img.shields.io/github/contributors/othneildrew/Best-README-Template.svg?style=flat-square
[contributors-url]: https://github.com/othneildrew/Best-README-Template/graphs/contributors
[forks-shield]: https://img.shields.io/github/forks/othneildrew/Best-README-Template.svg?style=flat-square
[forks-url]: https://github.com/othneildrew/Best-README-Template/network/members
[stars-shield]: https://img.shields.io/github/stars/othneildrew/Best-README-Template.svg?style=flat-square
[stars-url]: https://github.com/othneildrew/Best-README-Template/stargazers
[issues-shield]: https://img.shields.io/github/issues/othneildrew/Best-README-Template.svg?style=flat-square
[issues-url]: https://github.com/othneildrew/Best-README-Template/issues
[license-shield]: https://img.shields.io/github/license/othneildrew/Best-README-Template.svg?style=flat-square
[license-url]: https://github.com/othneildrew/Best-README-Template/blob/master/LICENSE.txt
[linkedin-shield]: https://img.shields.io/badge/-LinkedIn-black.svg?style=flat-square&logo=linkedin&colorB=555
[linkedin-url]: https://linkedin.com/in/othneildrew
[product-screenshot]: images/screenshot.png
