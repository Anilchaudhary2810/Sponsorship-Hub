import React, { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import Navbar from "../components/Navbar";
import AnalyticsPanel from "../components/AnalyticsPanel";
import { fetchDeals, fetchEvents, fetchCampaigns, fetchUserProfile } from "../services/api";
import "./AnalyticsPage.css";

const AnalyticsPage = () => {
  const navigate = useNavigate();
  const { userId } = useParams();
  const [loading, setLoading] = useState(true);
  const [targetUser, setTargetUser] = useState(null);
  const [data, setData] = useState({ deals: [], events: [], campaigns: [] });
  const [currentUser] = useState(() => JSON.parse(localStorage.getItem("currentUser") || "{}"));

  const targetId = userId || currentUser.id;

  useEffect(() => {
    const loadAllData = async () => {
      try {
        setLoading(true);
        // We need to know the target user's role to filter correctly
        const userResp = await fetchUserProfile(targetId);
        const user = userResp.data.user;
        setTargetUser(user);

        const [dealsResp, eventsResp, campaignsResp] = await Promise.all([
          fetchDeals(),
          fetchEvents(),
          fetchCampaigns()
        ]);

        let myDeals = dealsResp.data;
        let myEvents = eventsResp.data;
        let myCampaigns = campaignsResp.data;

        if (user.role === 'sponsor') {
          myDeals = myDeals.filter(d => Number(d.sponsor_id) === Number(targetId));
          myCampaigns = myCampaigns.filter(c => Number(c.creator_id) === Number(targetId));
          myEvents = []; 
        } else if (user.role === 'organizer') {
          myDeals = myDeals.filter(d => Number(d.organizer_id) === Number(targetId));
          myEvents = myEvents.filter(e => Number(e.organizer_id) === Number(targetId));
          myCampaigns = [];
        } else { // influencer
          myDeals = myDeals.filter(d => Number(d.influencer_id) === Number(targetId));
          myEvents = [];
          myCampaigns = []; 
        }

        setData({ deals: myDeals, events: myEvents, campaigns: myCampaigns });
      } catch (err) {
        console.error("Failed to load analytics data", err);
      } finally {
        setLoading(false);
      }
    };

    if (targetId) {
      loadAllData();
    } else {
      navigate("/login");
    }
  }, [targetId, navigate]);

  return (
    <div className="analytics-page-wrapper">
      <Navbar role={currentUser.role} />
      <div className="analytics-page-container">
        <header className="analytics-page-header">
          <button className="back-to-dash-btn" onClick={() => navigate(-1)}>
            ← Back
          </button>
          <div className="analytics-page-title-block">
            <h1>{targetId === currentUser.id ? "Your Intelligence" : `${targetUser?.full_name}'s Performance`}</h1>
            <p>Comprehensive data analysis for {targetId === currentUser.id ? "your" : "this"} {targetUser?.role} account</p>
          </div>
        </header>

        {loading ? (
          <div className="analytics-loading">
            <div className="spinner"></div>
            <p>Gathering performance metrics...</p>
          </div>
        ) : (
          <div className="analytics-content-box glass-morphism">
            <AnalyticsPanel 
              deals={data.deals} 
              events={data.events} 
              campaigns={data.campaigns} 
              role={targetUser?.role}
              title={targetId === currentUser.id ? "My Performance Report" : "Public Performance Audit"}
              subtitle={targetId === currentUser.id ? "Detailed breakdown of your partnerships and ROI" : `Analyzing ${targetUser?.full_name}'s marketplace activity`}
            />
          </div>
        )}
      </div>
    </div>
  );
};

export default AnalyticsPage;
